#!/usr/bin/env python3
"""Collect one person's commits for a calendar day across a namespace (default testdaily enterprise)."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import _gitee_http as gitee

DEFAULT_ORG = "testdaily"


def _scope_new_errors(errors: list[dict[str, str]], start: int, prefix: str) -> None:
    for item in errors[start:]:
        item["step"] = f"{prefix}:{item['step']}"


def _repo_has_person(
    api: str,
    owner: str,
    repo: str,
    token: str,
    person: str,
    max_pages: int,
    errors: list[dict[str, str]],
) -> tuple[bool, str | None, list[dict[str, Any]]]:
    owner_q, repo_q = gitee.repo_path(owner, repo)
    label = f"{owner}/{repo}"
    start = len(errors)
    collaborators, _ = gitee.fetch_collaborators(api, owner_q, repo_q, token, max_pages, errors)
    _scope_new_errors(errors, start, label)
    start = len(errors)
    contributors = gitee.fetch_contributors(api, owner_q, repo_q, token, errors)
    _scope_new_errors(errors, start, label)
    matched: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    how: str | None = None
    for u in collaborators:
        people.append(u)
        if gitee.user_matches_person(person, u):
            matched.append(u)
            how = "collaborator"
    for u in contributors:
        people.append(u)
        if gitee.user_matches_person(person, u):
            matched.append(u)
            if how is None:
                how = "contributor"
    return bool(matched), how, people


def _collect_repo_commits(
    api: str,
    owner: str,
    repo: str,
    token: str,
    needles: list[str],
    since: str,
    until: str,
    max_pages: int,
    sleep_s: float,
    errors: list[dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], list[str], bool]:
    owner_q, repo_q = gitee.repo_path(owner, repo)
    label = f"{owner}/{repo}"
    start = len(errors)
    branches, br_truncated = gitee.fetch_branches(api, owner_q, repo_q, token, max_pages, errors)
    _scope_new_errors(errors, start, label)
    by_sha: dict[str, dict[str, Any]] = {}
    truncated = br_truncated
    for i, branch in enumerate(branches):
        start = len(errors)
        commits, c_truncated = gitee.fetch_commits(
            api,
            owner_q,
            repo_q,
            token,
            {"sha": branch, "since": since, "until": until},
            max_pages,
            errors,
        )
        _scope_new_errors(errors, start, f"{label}@{branch}")
        if c_truncated:
            truncated = True
        for c in commits:
            if not gitee.commit_matches_any_person(needles, c):
                continue
            sha = c.get("sha")
            if not sha:
                continue
            existing = by_sha.get(sha)
            if existing:
                if branch not in existing["branches"]:
                    existing["branches"].append(branch)
                continue
            row = dict(c)
            row["repo"] = f"{owner}/{repo}"
            row["branches"] = [branch]
            by_sha[sha] = row
        if sleep_s and i + 1 < len(branches):
            time.sleep(sleep_s)
    return by_sha, branches, truncated


def main() -> int:
    p = argparse.ArgumentParser(description="Daily commits for one person across an enterprise or org")
    gitee.add_auth_args(p)
    p.add_argument(
        "--org",
        default=DEFAULT_ORG,
        help="Enterprise or organization path (default testdaily, an enterprise)",
    )
    p.add_argument(
        "--namespace-type",
        choices=("auto", "enterprise", "org"),
        default="auto",
        help="auto tries enterprise first, then org only on HTTP 404",
    )
    p.add_argument("--person", required=True, help="Gitee login, name, or email")
    p.add_argument("--date", required=True, help="Calendar day YYYY-MM-DD (Asia/Shanghai)")
    p.add_argument("--details-limit", type=int, default=20, help="Hydrate this many unique SHAs with diffs")
    p.add_argument("--max-pages", type=int, default=50)
    p.add_argument("--sleep", type=float, default=0.15)
    p.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Parallel repo scans (default 8). 1 keeps the old serial loop and --sleep pacing",
    )
    p.add_argument(
        "--http-timeout",
        type=float,
        default=10,
        help="Seconds for each Gitee GET (default 10). Other scripts stay at 30 unless they call configure_http",
    )
    args = p.parse_args()
    gitee.apply_token(args)

    api = args.api_base.rstrip("/")
    workers = max(1, args.concurrency)
    gitee.configure_http(timeout=args.http_timeout)
    inner_sleep = 0.0 if workers > 1 else args.sleep
    since, until = gitee.day_bounds_iso(args.date)
    errors: list[dict[str, str]] = []
    repos, repos_truncated, namespace_type = gitee.fetch_namespace_repos(
        api, args.org, args.token, args.max_pages, errors, namespace_type=args.namespace_type
    )

    matched_repos: list[dict[str, Any]] = []
    all_by_sha: dict[str, dict[str, Any]] = {}
    any_truncated = repos_truncated
    person_needles: list[str] = gitee.identity_needles_for_person(args.person, [])

    def scan_repo(repo: dict[str, Any]) -> dict[str, Any]:
        local_errors: list[dict[str, str]] = []
        owner = repo.get("owner") or args.org
        name = repo.get("name") or ""
        base: dict[str, Any] = {
            "hit": False,
            "errors": local_errors,
            "owner": owner,
            "name": name,
            "repo": repo,
        }
        if not name:
            return base
        hit, how, people = _repo_has_person(
            api, owner, name, args.token, args.person, args.max_pages, local_errors
        )
        if not hit:
            return base
        needles = gitee.identity_needles_for_person(args.person, people)
        by_sha, branches, truncated = _collect_repo_commits(
            api,
            owner,
            name,
            args.token,
            needles,
            since,
            until,
            args.max_pages,
            inner_sleep,
            local_errors,
        )
        return {
            "hit": True,
            "errors": local_errors,
            "owner": owner,
            "name": name,
            "repo": repo,
            "how": how,
            "needles": needles,
            "by_sha": by_sha,
            "branches": branches,
            "truncated": truncated,
        }

    if workers <= 1:
        scanned: list[dict[str, Any]] = []
        for i, repo in enumerate(repos):
            scanned.append(scan_repo(repo))
            if args.sleep and i + 1 < len(repos):
                time.sleep(args.sleep)
    else:
        scanned = gitee.bounded_map(scan_repo, repos, workers)

    for row in scanned:
        errors.extend(row["errors"])
        if not row["hit"]:
            continue
        for n in row["needles"]:
            if n not in person_needles:
                person_needles.append(n)
        if row["truncated"]:
            any_truncated = True
        repo = row["repo"]
        owner = row["owner"]
        name = row["name"]
        matched_repos.append(
            {
                "full_name": repo.get("full_name") or f"{owner}/{name}",
                "matched_as": row["how"],
                "branch_count": len(row["branches"]),
                "commit_count": len(row["by_sha"]),
            }
        )
        for sha, item in row["by_sha"].items():
            existing = all_by_sha.get(sha)
            if existing:
                for b in item["branches"]:
                    if b not in existing["branches"]:
                        existing["branches"].append(b)
            else:
                all_by_sha[sha] = item

    commits = list(all_by_sha.values())
    commits.sort(key=lambda c: c.get("authored_at") or "", reverse=True)

    details: list[dict[str, Any]] = []
    details_truncated = False
    if args.details_limit and commits:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for c in commits:
            grouped.setdefault(c["repo"], []).append(c)
        remaining = args.details_limit
        for repo_path, group in grouped.items():
            if remaining <= 0:
                details_truncated = True
                break
            owner, name = repo_path.split("/", 1)
            owner_q, repo_q = gitee.repo_path(owner, name)
            take = group[:remaining]
            start = len(errors)
            part, more = gitee.fetch_commit_details(
                api, owner_q, repo_q, args.token, take, len(take), inner_sleep, errors
            )
            _scope_new_errors(errors, start, repo_path)
            details.extend(part)
            remaining -= len(take)
            if more:
                details_truncated = True

    gitee.write_json(
        {
            "org": args.org,
            "namespace_type": namespace_type,
            "person": args.person,
            "person_needles": person_needles,
            "date": args.date,
            "since": since,
            "until": until,
            "auth": {
                "token_present": bool(args.token),
                "token_source": getattr(args, "token_source", None),
            },
            "repos_matched": matched_repos,
            "commits": commits,
            "commit_details": details,
            "meta": {
                "org_repo_count": len(repos),
                "matched_repo_count": len(matched_repos),
                "commit_count": len(commits),
                "detail_count": len(details),
                "repos_truncated": repos_truncated,
                "truncated": any_truncated,
                "details_truncated": details_truncated,
                "max_pages": args.max_pages,
                "details_limit": args.details_limit,
                "concurrency": workers,
                "http_timeout": args.http_timeout,
            },
            "errors": errors,
        },
        args.out,
    )
    return 0 if namespace_type else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
