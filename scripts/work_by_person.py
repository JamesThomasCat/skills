#!/usr/bin/env python3
"""Fetch users + commits + limited diffs, then group work by person."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Any

import _gitee_http as gitee


def _match_key(
    commit: dict[str, Any],
    collaborators: list[dict[str, Any]],
    contributors: list[dict[str, Any]],
) -> tuple[str, str]:
    login = commit.get("author_login") or ""
    email = (commit.get("author_email") or "").lower()
    name = commit.get("author_name") or ""

    if login:
        for m in collaborators:
            if m.get("login") == login:
                return "login", login
        return "login", login

    if email:
        for t in contributors:
            if (t.get("email") or "").lower() == email:
                return "email", email

    if name:
        for m in collaborators:
            if m.get("name") == name:
                return "login", m.get("login") or name
        for t in contributors:
            if t.get("name") == name:
                em = (t.get("email") or "").lower()
                return ("email", em) if em else ("name", name)
        return "name", name

    return "raw", login or email or "unknown"


def _person_shell(key: tuple[str, str], collaborators: list[dict[str, Any]], contributors: list[dict[str, Any]]) -> dict[str, Any]:
    kind, value = key
    login = value if kind == "login" else None
    email = value if kind == "email" else None
    name = value if kind == "name" else None
    member = next((m for m in collaborators if login and m.get("login") == login), None)
    contrib = next((t for t in contributors if email and (t.get("email") or "").lower() == email), None)
    if member is None and name:
        member = next((m for m in collaborators if m.get("name") == name), None)
    if contrib is None and name:
        contrib = next((t for t in contributors if t.get("name") == name), None)

    identities = []
    if member:
        identities.append("成员")
        login = login or member.get("login")
        name = name or member.get("name")
    if contrib:
        identities.append("贡献者")
        email = email or contrib.get("email")
        name = name or contrib.get("name")
    if not identities:
        identities.append("仅提交作者")

    display = name or login or email or value
    return {
        "key": f"{kind}:{value}",
        "display_name": display,
        "login": login,
        "email": email,
        "identity": identities,
        "permissions": (member or {}).get("permissions"),
        "member_role": (member or {}).get("member_role"),
        "contributions": (contrib or {}).get("contributions"),
        "commit_count": 0,
        "zero_commit": True,
        "files": [],
        "commits": [],
    }


def group_people(
    collaborators: list[dict[str, Any]],
    contributors: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    details_by_sha = {d.get("sha"): d for d in details if d.get("sha")}
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    file_counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for c in commits:
        key = _match_key(c, collaborators, contributors)
        if key not in groups:
            groups[key] = _person_shell(key, collaborators, contributors)
        person = groups[key]
        person["zero_commit"] = False
        person["commit_count"] += 1
        sha = c.get("sha")
        detail = details_by_sha.get(sha) or {}
        files = detail.get("files") or []
        for f in files:
            fn = f.get("filename")
            if fn:
                file_counts[key][fn] += 1
        person["commits"].append(
            {
                "sha": sha,
                "message": c.get("message"),
                "authored_at": c.get("authored_at"),
                "author_login": c.get("author_login"),
                "author_name": c.get("author_name"),
                "author_email": c.get("author_email"),
                "files": [f.get("filename") for f in files if f.get("filename")],
                "has_detail": bool(detail),
            }
        )

    seen_logins = {p.get("login") for p in groups.values() if p.get("login")}
    for m in collaborators:
        login = m.get("login")
        if login and login not in seen_logins:
            key = ("login", login)
            groups[key] = _person_shell(key, collaborators, contributors)

    people = list(groups.values())
    for person in people:
        key = tuple(person["key"].split(":", 1))
        ranked = sorted(file_counts.get(key, {}).items(), key=lambda kv: (-kv[1], kv[0]))
        person["files"] = [{"filename": n, "commit_hits": n_hits} for n, n_hits in ranked]
        person["commits"].sort(key=lambda x: x.get("authored_at") or "", reverse=True)

    people.sort(key=lambda p: (-p["commit_count"], p.get("login") or p.get("display_name") or ""))
    return people


def main() -> int:
    p = argparse.ArgumentParser(description="Group Gitee repo work by person")
    gitee.add_common_args(p)
    p.add_argument("--sha", default="", help="Branch name or starting SHA")
    p.add_argument("--since", default="", help="ISO 8601 start time")
    p.add_argument("--until", default="", help="ISO 8601 end time")
    p.add_argument("--author", default="", help="Filter commits by email or login")
    p.add_argument("--path", default="", help="Only commits touching this file path")
    p.add_argument("--details-limit", type=int, default=40, help="How many commits to hydrate with diffs; 0 = none")
    p.add_argument("--max-pages", type=int, default=50, help="Safety cap for paginated lists")
    p.add_argument("--sleep", type=float, default=0.15, help="Seconds between detail requests")
    args = p.parse_args()
    gitee.apply_token(args)

    api = args.api_base.rstrip("/")
    owner_q, repo_q = gitee.repo_path(args.owner, args.repo)
    errors: list[dict[str, str]] = []

    collaborators, collab_truncated = gitee.fetch_collaborators(
        api, owner_q, repo_q, args.token, args.max_pages, errors
    )
    contributors = gitee.fetch_contributors(api, owner_q, repo_q, args.token, errors)
    query = {
        "sha": args.sha,
        "since": args.since,
        "until": args.until,
        "author": args.author,
        "path": args.path,
    }
    commits, commits_truncated = gitee.fetch_commits(
        api, owner_q, repo_q, args.token, query, args.max_pages, errors
    )
    details, details_truncated = gitee.fetch_commit_details(
        api, owner_q, repo_q, args.token, commits, args.details_limit, args.sleep, errors
    )
    people = group_people(collaborators, contributors, commits, details)

    gitee.write_json(
        gitee.envelope(
            args.owner,
            args.repo,
            api,
            args.token,
            {
                "filters": {
                    "sha": args.sha or None,
                    "since": args.since or None,
                    "until": args.until or None,
                    "author": args.author or None,
                    "path": args.path or None,
                },
                "collaborators": collaborators,
                "contributors": contributors,
                "commits": commits,
                "commit_details": details,
                "people": people,
                "meta": {
                    "collaborator_count": len(collaborators),
                    "contributor_count": len(contributors),
                    "commit_count": len(commits),
                    "detail_count": len(details),
                    "people_count": len(people),
                    "collaborators_truncated": collab_truncated,
                    "commits_truncated": commits_truncated,
                    "details_truncated": details_truncated,
                    "max_pages": args.max_pages,
                    "details_limit": args.details_limit,
                },
                "errors": errors,
            },
            token_source=getattr(args, "token_source", None),
        ),
        args.out,
    )
    return 0 if not any(e["step"] == "commits" for e in errors) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
