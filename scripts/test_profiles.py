"""Offline tests for persisted profiles and the diary's scan/cache paths."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import _gitee_http as gitee
import _profiles as profiles
import daily_report
import query_profile
import save_profile


@contextmanager
def profile_test_dir():
    # Windows sandbox denies writes inside tempfile.TemporaryDirectory's private ACL.
    path = Path.cwd() / "tests" / f"profile-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield str(path)
    finally:
        if Path.cwd().resolve() not in path.resolve().parents:
            raise AssertionError("test cleanup path escaped the workspace")
        shutil.rmtree(path)


class ProfileDiaryTest(unittest.TestCase):
    def test_full_scan_creates_profile_cache_reuses_it_and_full_refreshes_it(self):
        calls = {"namespace": 0, "branches": 0, "commits": 0}
        repos = [
            {"owner": "testdaily", "name": "student", "full_name": "testdaily/student"},
            {"owner": "testdaily", "name": "unrelated", "full_name": "testdaily/unrelated"},
        ]
        member = {"login": "meiyanxin", "name": "梅艳欣", "email": "may@example.com"}

        def fetch_namespace(*args, **kwargs):
            calls["namespace"] += 1
            return repos, False, "enterprise"

        def fetch_members(api, owner, repo, token, max_pages, errors):
            return ([member] if repo == "student" else []), False

        def fetch_branches(api, owner, repo, token, max_pages, errors):
            calls["branches"] += 1
            return ["main", "feature"], False

        def fetch_commits(api, owner, repo, token, query, max_pages, errors):
            calls["commits"] += 1
            return [{"sha": "abc", "message": "Student work", "author_login": None,
                     "author_name": "thoamsmay", "author_email": "may@example.com",
                     "committer_login": None, "authored_at": "2026-09-19T10:00:00+08:00"}], False

        with profile_test_dir() as temp_dir:
            out = str(Path(temp_dir) / "daily.json")
            argv = ["daily_report.py", "--person", "meiyanxin", "--date", "2026-09-19",
                    "--profile-dir", temp_dir, "--out", out, "--details-limit", "0"]
            with (
                patch.object(sys, "argv", argv),
                patch.object(gitee, "fetch_namespace_repos", fetch_namespace),
                patch.object(gitee, "fetch_collaborators", fetch_members),
                patch.object(gitee, "fetch_contributors", return_value=[]),
                patch.object(gitee, "fetch_branches", fetch_branches),
                patch.object(gitee, "fetch_commits", fetch_commits),
                patch.object(daily_report.random, "random", return_value=0.8),
            ):
                self.assertEqual(daily_report.main(), 0)
                first = json.loads(Path(out).read_text(encoding="utf-8"))
                self.assertEqual(first["profile_mode"], "full")
                self.assertEqual(first["meta"]["commit_count"], 1)
                self.assertEqual(first["commits"][0]["branches"], ["main", "feature"])
                self.assertEqual(calls["namespace"], 1)
                self.assertEqual(calls["branches"], 1)

                saved = profiles.find_profile(profiles.load_store("testdaily", temp_dir), "meiyanxin")
                self.assertIsNotNone(saved)
                self.assertEqual(saved["identity"], member)
                self.assertEqual([r["name"] for r in saved["repositories"]], ["student"])
                self.assertEqual([r["name"] for r in saved["authorized_repositories"]], ["student"])
                self.assertEqual(saved["repositories"][0]["branches"], ["main", "feature"])
                self.assertTrue(saved["complete"])

                self.assertEqual(daily_report.main(), 0)
                second = json.loads(Path(out).read_text(encoding="utf-8"))
                self.assertEqual(second["profile_mode"], "profile")
                self.assertEqual(calls["namespace"], 1)
                self.assertEqual(calls["branches"], 1)

                with patch.object(daily_report.random, "random", return_value=0.2):
                    self.assertEqual(daily_report.main(), 0)
                third = json.loads(Path(out).read_text(encoding="utf-8"))
                self.assertEqual(third["profile_mode"], "full")
                self.assertEqual(calls["namespace"], 2)
                self.assertEqual(calls["branches"], 2)
                self.assertEqual(calls["commits"], 6)

            query_out = str(Path(temp_dir) / "query.json")
            with patch.object(sys, "argv", ["query_profile.py", "--keyword", "may@example.com",
                                            "--profile-dir", temp_dir, "--out", query_out]):
                self.assertEqual(query_profile.main(), 0)
            result = json.loads(Path(query_out).read_text(encoding="utf-8"))
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["profiles"][0]["repositories"][0]["name"], "student")

    def test_namespace_files_and_incomplete_profiles_are_separate(self):
        with profile_test_dir() as temp_dir:
            base = {"query": "meiyanxin", "identity": {"login": "meiyanxin", "name": None,
                                                      "email": None}, "aliases": ["meiyanxin"],
                    "repositories": [], "complete": False}
            paths = []
            for namespace in ("testdaily", "other-company"):
                paths.append(profiles.save_profile({**base, "namespace": namespace}, temp_dir))
            self.assertNotEqual(paths[0], paths[1])
            self.assertFalse(profiles.load_store("testdaily", temp_dir)["profiles"][0]["complete"])
            self.assertEqual(profiles.load_store("other-company", temp_dir)["profiles"][0]["namespace"],
                             "other-company")
            out = str(Path(temp_dir) / "all.json")
            with patch.object(sys, "argv", ["query_profile.py", "--keyword", "meiyanxin",
                                            "--all-namespaces", "--profile-dir", temp_dir,
                                            "--out", out]):
                self.assertEqual(query_profile.main(), 0)
            self.assertEqual(json.loads(Path(out).read_text(encoding="utf-8"))["count"], 2)

    def test_save_entry_records_partial_scan_without_treating_it_as_complete(self):
        def failed_contributors(api, owner, repo, token, errors):
            errors.append({"step": "contributors", "error": "HTTP 503"})
            return []

        with profile_test_dir() as temp_dir:
            out = str(Path(temp_dir) / "saved.json")
            argv = ["save_profile.py", "--person", "meiyanxin", "--profile-dir", temp_dir,
                    "--out", out]
            with (
                patch.object(sys, "argv", argv),
                patch.object(gitee, "fetch_namespace_repos", return_value=(
                    [{"owner": "testdaily", "name": "student"}], False, "enterprise")),
                patch.object(gitee, "fetch_collaborators", return_value=(
                    [{"login": "meiyanxin", "name": "梅艳欣", "email": "may@example.com"}], False)),
                patch.object(gitee, "fetch_contributors", failed_contributors),
                patch.object(gitee, "fetch_branches", return_value=(["main"], False)),
            ):
                self.assertEqual(save_profile.main(), 0)
            result = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertFalse(result["profile"]["complete"])
            self.assertEqual(result["errors"][0]["step"], "testdaily/student:contributors")
            stored = profiles.load_store("testdaily", temp_dir)["profiles"][0]
            self.assertFalse(stored["complete"])
            self.assertEqual(stored["repositories"][0]["branches"], ["main"])

    def test_shared_email_finds_repo_with_different_contributor_name(self):
        repos = [{"owner": "testdaily", "name": name} for name in ("first", "second")]

        def members(api, owner, repo, token, max_pages, errors):
            return ([{"login": "meiyanxin", "name": "梅艳欣", "email": "may@example.com"}]
                    if repo == "first" else []), False

        def contributors(api, owner, repo, token, errors):
            return ([{"login": None, "name": "thoamsmay", "email": "may@example.com"}]
                    if repo == "second" else [])

        with (
            patch.object(gitee, "fetch_namespace_repos", return_value=(repos, False, "enterprise")),
            patch.object(gitee, "fetch_collaborators", members),
            patch.object(gitee, "fetch_contributors", contributors),
            patch.object(gitee, "fetch_branches", return_value=(["main"], False)),
        ):
            profile, errors = profiles.scan_profile("api", "testdaily", "meiyanxin", "", 1, 2)
        self.assertEqual(errors, [])
        self.assertEqual([repo["name"] for repo in profile["repositories"]], ["first", "second"])
        self.assertEqual([repo["name"] for repo in profile["authorized_repositories"]], ["first"])
        self.assertIn("thoamsmay", profile["aliases"])
        self.assertIn("may@example.com", profile["repositories"][1]["identity_needles"])
        self.assertIn("thoamsmay", profile["repositories"][1]["identity_needles"])


if __name__ == "__main__":
    unittest.main()
