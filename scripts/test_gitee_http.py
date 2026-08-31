#!/usr/bin/env python3
"""Unit tests for namespace repo listing. Not a user-facing entry script."""

from __future__ import annotations

import unittest
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


if __name__ == "__main__":
    unittest.main()
