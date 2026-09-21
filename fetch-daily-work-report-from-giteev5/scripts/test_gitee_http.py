#!/usr/bin/env python3
"""Unit tests for namespace repo listing. Not a user-facing entry script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _gitee_http as gitee

ENTERPRISE_REPO = {
    "path": "app",
    "name": "app",
    "full_name": "testdaily/app",
    "owner": {"login": "testdaily"},
    "html_url": "https://gitee.com/testdaily/app",
    "private": True,
    "default_branch": "master",
}

# Gitee enterprise list often returns the creator as owner.login, not the enterprise path.
ENTERPRISE_REPO_CREATOR_OWNER = {
    "path": "app",
    "name": "app",
    "full_name": "cuizhaoy/app",
    "owner": {"login": "cuizhaoy"},
    "html_url": "https://gitee.com/testdaily/app",
    "private": True,
    "default_branch": "master",
}

ORG_REPO = {
    "path": "demo",
    "name": "demo",
    "full_name": "someorg/demo",
    "owner": {"login": "someorg"},
    "html_url": "https://gitee.com/someorg/demo",
    "private": False,
    "default_branch": "master",
}


def _http_error(code: int, path: str) -> RuntimeError:
    return RuntimeError(f"HTTP {code} Not Found for {path}: {{}}")


class FetchNamespaceReposTest(unittest.TestCase):
    def test_auto_hits_enterprise_first_and_skips_org_when_it_works(self):
        calls: list[str] = []

        def fake_paginate(api, path, token, query, max_pages):
            calls.append(path)
            if path == "/enterprises/testdaily/repos":
                return [ENTERPRISE_REPO], False
            raise AssertionError(f"should not call {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5", "testdaily", "tok", 1, errors
            )

        self.assertEqual(kind, "enterprise")
        self.assertFalse(truncated)
        self.assertEqual([r["name"] for r in repos], ["app"])
        self.assertEqual(calls, ["/enterprises/testdaily/repos"])
        self.assertEqual(errors, [])

    def test_auto_falls_back_to_org_only_on_enterprise_404(self):
        calls: list[str] = []

        def fake_paginate(api, path, token, query, max_pages):
            calls.append(path)
            if path == "/enterprises/someorg/repos":
                raise _http_error(404, path)
            if path == "/orgs/someorg/repos":
                return [ORG_REPO], False
            raise AssertionError(f"unexpected {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5", "someorg", "tok", 1, errors
            )

        self.assertEqual(kind, "org")
        self.assertEqual([r["name"] for r in repos], ["demo"])
        self.assertEqual(
            calls,
            ["/enterprises/someorg/repos", "/orgs/someorg/repos"],
        )
        self.assertEqual(errors, [])

    def test_auto_does_not_fall_back_on_enterprise_401(self):
        calls: list[str] = []

        def fake_paginate(api, path, token, query, max_pages):
            calls.append(path)
            if path == "/enterprises/testdaily/repos":
                raise RuntimeError(f"HTTP 401 Unauthorized for {path}: {{}}")
            raise AssertionError(f"should not call {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5", "testdaily", "tok", 1, errors
            )

        self.assertIsNone(kind)
        self.assertEqual(repos, [])
        self.assertEqual(calls, ["/enterprises/testdaily/repos"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["step"], "enterprise_repos")

    def test_namespace_type_org_skips_enterprise(self):
        calls: list[str] = []

        def fake_paginate(api, path, token, query, max_pages):
            calls.append(path)
            if path == "/orgs/someorg/repos":
                return [ORG_REPO], False
            raise AssertionError(f"should not call {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5",
                "someorg",
                "tok",
                1,
                errors,
                namespace_type="org",
            )

        self.assertEqual(kind, "org")
        self.assertEqual(calls, ["/orgs/someorg/repos"])
        self.assertEqual(errors, [])

    def test_enterprise_repo_owner_is_enterprise_path_not_creator_login(self):
        def fake_paginate(api, path, token, query, max_pages):
            if path == "/enterprises/testdaily/repos":
                return [ENTERPRISE_REPO_CREATOR_OWNER], False
            raise AssertionError(f"should not call {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5", "testdaily", "tok", 1, errors
            )

        self.assertEqual(kind, "enterprise")
        self.assertFalse(truncated)
        self.assertEqual(errors, [])
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["owner"], "testdaily")
        self.assertEqual(repos[0]["name"], "app")
        self.assertEqual(repos[0]["full_name"], "testdaily/app")

    def test_org_repo_keeps_owner_login(self):
        def fake_paginate(api, path, token, query, max_pages):
            if path == "/orgs/someorg/repos":
                return [ORG_REPO], False
            raise AssertionError(f"should not call {path}")

        errors: list[dict[str, str]] = []
        with patch.object(gitee, "paginate", fake_paginate):
            repos, truncated, kind = gitee.fetch_namespace_repos(
                "https://gitee.com/api/v5",
                "someorg",
                "tok",
                1,
                errors,
                namespace_type="org",
            )

        self.assertEqual(kind, "org")
        self.assertEqual(repos[0]["owner"], "someorg")
        self.assertEqual(repos[0]["full_name"], "someorg/demo")


class PersonIdentityTest(unittest.TestCase):
    """Git author name can differ from Gitee contributor name when email is shared."""

    CONTRIBUTOR = {
        "login": None,
        "name": "meiyanxin",
        "email": "shared@example.com",
    }
    COMMIT = {
        "author_login": None,
        "author_name": "thoamsmay",
        "author_email": "shared@example.com",
        "committer_login": None,
    }
    OTHER_COMMIT = {
        "author_login": None,
        "author_name": "someone-else",
        "author_email": "other@example.com",
        "committer_login": None,
    }

    def test_name_needle_does_not_match_renamed_git_author(self):
        self.assertTrue(gitee.user_matches_person("meiyanxin", self.CONTRIBUTOR))
        self.assertFalse(gitee.commit_matches_person("meiyanxin", self.COMMIT))

    def test_needles_from_matched_user_include_email(self):
        needles = gitee.identity_needles_for_person("meiyanxin", [self.CONTRIBUTOR])
        folded = {n.casefold() for n in needles}
        self.assertIn("meiyanxin", folded)
        self.assertIn("shared@example.com", folded)

    def test_commit_matches_via_contributor_email_alias(self):
        needles = gitee.identity_needles_for_person("meiyanxin", [self.CONTRIBUTOR])
        self.assertTrue(gitee.commit_matches_any_person(needles, self.COMMIT))
        self.assertFalse(gitee.commit_matches_any_person(needles, self.OTHER_COMMIT))

    def test_shared_email_adds_renamed_git_author(self):
        users = [
            self.CONTRIBUTOR,
            {"login": None, "name": "thoamsmay", "email": "shared@example.com"},
        ]
        needles = gitee.identity_needles_for_person("meiyanxin", users)
        folded = {n.casefold() for n in needles}
        self.assertIn("thoamsmay", folded)
        self.assertTrue(gitee.commit_matches_any_person(needles, self.COMMIT))


class HttpClientConfigTest(unittest.TestCase):
    def tearDown(self) -> None:
        gitee.configure_http(timeout=30)

    def test_request_json_uses_configured_timeout(self):
        captured: dict[str, object] = {}

        class FakeResp:
            status = 200

            def read(self):
                return b'{"ok": true}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=None):
            captured["timeout"] = timeout
            return FakeResp()

        gitee.configure_http(timeout=10)
        with patch.object(gitee.urllib.request, "urlopen", fake_urlopen):
            data = gitee.request_json("https://gitee.com/api/v5/ping", "")
        self.assertEqual(captured["timeout"], 10)
        self.assertEqual(data, {"ok": True})


class SkillRenameTest(unittest.TestCase):
    def test_default_user_env_path_uses_current_skill_name(self):
        self.assertEqual(
            gitee.default_user_env_path().parts[-2:],
            (".fetch-daily-work-report-from-giteev5", "env"),
        )

    def test_resolve_token_falls_back_to_legacy_user_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current_path = root / ".fetch-daily-work-report-from-giteev5" / "env"
            legacy_path = root / ".gitee-auto" / "env"
            legacy_path.parent.mkdir(parents=True)
            legacy_path.write_text("GITEE_ACCESS_TOKEN=legacy-token\n", encoding="utf-8")

            with (
                patch.object(gitee, "default_user_env_path", return_value=current_path),
                patch.object(gitee, "legacy_user_env_path", return_value=legacy_path),
            ):
                token, source = gitee.resolve_token(environ={}, skill_root=root / "skill")

        self.assertEqual(token, "legacy-token")
        self.assertEqual(source, "user_env")


class BoundedMapTest(unittest.TestCase):
    def test_preserves_order_with_workers(self):
        def work(n: int) -> int:
            return n * 2

        self.assertEqual(gitee.bounded_map(work, [3, 1, 2], workers=4), [6, 2, 4])

    def test_workers_one_runs_inline(self):
        seen: list[int] = []

        def work(n: int) -> int:
            seen.append(n)
            return n

        self.assertEqual(gitee.bounded_map(work, [1, 2, 3], workers=1), [1, 2, 3])
        self.assertEqual(seen, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
