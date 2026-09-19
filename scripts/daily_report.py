#!/usr/bin/env python3
"""Collect one person's commits for a calendar day across a namespace (default testdaily enterprise)."""

from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Any

import _gitee_http as gitee
import _profiles as profiles

DEFAULT_ORG = "testdaily"


def _scope_new_errors(errors: list[dict[str, str]], start: int, prefix: str) -> None:
    for item in errors[start:]:
        item["step"] = f"{prefix}:{item['step']}"


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
    branches: list[str],
) -> tuple[dict[str, dict[str, Any]], bool]:
    owner_q, repo_q = gitee.repo_path(owner, repo)
    label = f"{owner}/{repo}"
    by_sha: dict[str, dict[str, Any]] = {}
    truncated = False
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
    return by_sha, truncated


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
    p.add_argument("--profile-dir", default="", help="Profile storage directory (default: skill/profiles)")
    p.add_argument(
        "--refresh-mode", choices=("auto", "full", "profile"), default="auto",
        help="auto randomly chooses; profile falls back to full when no complete profile exists",
    )
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
    if args.details_limit < 0 or args.max_pages < 1:
        p.error("--details-limit must be >= 0 and --max-pages must be >= 1")
    gitee.apply_token(args)

    api = args.api_base.rstrip("/")
    workers = max(1, args.concurrency)
    gitee.configure_http(timeout=args.http_timeout)
    inner_sleep = 0.0 if workers > 1 else args.sleep
    since, until = gitee.day_bounds_iso(args.date)
    errors: list[dict[str, str]] = []
    store = profiles.load_store(args.org, args.profile_dir)
    profile = profiles.find_profile(store, args.person)
    profile_usable = bool(
        profile and profile.get("complete")
        and (args.namespace_type == "auto" or profile.get("namespace_type") == args.namespace_type)
    )
    use_profile = profile_usable and (
        args.refresh_mode == "profile" or (args.refresh_mode == "auto" and random.random() >= 0.5)
    )
    if use_profile:
        mode = "profile"
        assert profile is not None
    else:
        mode = "full"
        profile, profile_errors = profiles.scan_profile(
            api, args.org, args.person, args.token, args.max_pages, workers,
            namespace_type=args.namespace_type,
        )
        errors.extend(profile_errors)
        if profile.get("namespace_type"):
            profiles.save_profile(profile, args.profile_dir)

    namespace_type = profile.get("namespace_type")
    repo_inventory = profile.get("repositories") or []
    scan_meta = profile.get("scan_meta") or {}

    matched_repos: list[dict[str, Any]] = []
    all_by_sha: dict[str, dict[str, Any]] = {}
    any_truncated = bool(scan_meta.get("truncated"))
    person_needles = profile.get("aliases") or [args.person]

    def scan_repo(repo: dict[str, Any]) -> dict[str, Any]:
        local_errors: list[dict[str, str]] = []
        owner = repo["owner"]
        name = repo["name"]
        by_sha, truncated = _collect_repo_commits(
            api,
            owner,
            name,
            args.token,
            repo.get("identity_needles") or person_needles,
            since,
            until,
            args.max_pages,
            inner_sleep,
            local_errors,
            repo.get("branches") or [],
        )
        return {
            "errors": local_errors,
            "repo": repo,
            "by_sha": by_sha,
            "truncated": truncated,
        }

    if workers <= 1:
        scanned: list[dict[str, Any]] = []
        for i, repo in enumerate(repo_inventory):
            scanned.append(scan_repo(repo))
            if args.sleep and i + 1 < len(repo_inventory):
                time.sleep(args.sleep)
    else:
        scanned = gitee.bounded_map(scan_repo, repo_inventory, workers)

    for row in scanned:
        errors.extend(row["errors"])
        if row["truncated"]:
            any_truncated = True
        repo = row["repo"]
        owner = repo["owner"]
        name = repo["name"]
        matched_repos.append(
            {
                "full_name": repo.get("full_name") or f"{owner}/{name}",
                "matched_as": repo.get("matched_as"),
                "branch_count": len(repo.get("branches") or []),
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
    details_truncated = len(commits) > args.details_limit
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
            "profile_mode": mode,
            "profile_path": str(profiles.profile_path(args.org, args.profile_dir)),
            "profile_updated_at": profile.get("updated_at"),
            "profile_complete": profile.get("complete"),
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
                "org_repo_count": scan_meta.get("repo_count"),
                "matched_repo_count": len(matched_repos),
                "commit_count": len(commits),
                "detail_count": len(details),
                "repos_truncated": scan_meta.get("truncated"),
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
