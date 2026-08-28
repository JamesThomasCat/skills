#!/usr/bin/env python3
"""Fetch Gitee repository members, contributors, commits, and commit diffs.

Auth: GITEE_ACCESS_TOKEN or --token. Never print the token.
Default API base: https://gitee.com/api/v5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_API_BASE = "https://gitee.com/api/v5"
MAX_PER_PAGE = 100
PATCH_CHARS = 4000


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Gitee repo users, commits, and diffs")
    p.add_argument("--owner", required=True, help="Namespace path (user/org/enterprise)")
    p.add_argument("--repo", required=True, help="Repository path")
    p.add_argument("--api-base", default=os.environ.get("GITEE_API_BASE", DEFAULT_API_BASE))
    p.add_argument("--token", default=os.environ.get("GITEE_ACCESS_TOKEN", ""))
    p.add_argument("--sha", default="", help="Branch name or starting SHA for commit list")
    p.add_argument("--since", default="", help="ISO 8601 start time")
    p.add_argument("--until", default="", help="ISO 8601 end time")
    p.add_argument("--author", default="", help="Filter commits by email or login")
    p.add_argument("--path", default="", help="Only commits touching this file path")
    p.add_argument("--details-limit", type=int, default=40, help="How many commits to hydrate with files/patch; 0 = none")
    p.add_argument("--max-pages", type=int, default=50, help="Safety cap for paginated lists")
    p.add_argument("--sleep", type=float, default=0.15, help="Seconds between detail requests")
    p.add_argument("--out", default="", help="Write JSON here; default stdout")
    return p.parse_args()


def request_json(url: str, token: str, query: dict[str, Any] | None = None) -> Any:
    parsed = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(parsed.query))
    if query:
        for k, v in query.items():
            if v is None or v == "":
                continue
            q[k] = str(v)
    full = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(q), parsed.fragment)
    )
    headers = {
        "Accept": "application/json",
        "User-Agent": "gitee-auto-skill/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(full, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} {e.reason} for {parsed.path}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error for {parsed.path}: {e.reason}") from e
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON (HTTP {status}) for {parsed.path}: {e}") from e


def paginate(
    api_base: str,
    path: str,
    token: str,
    query: dict[str, Any],
    max_pages: int,
) -> tuple[list[Any], bool]:
    items: list[Any] = []
    truncated = False
    for page in range(1, max_pages + 1):
        q = dict(query)
        q["page"] = page
        q["per_page"] = MAX_PER_PAGE
        data = request_json(f"{api_base.rstrip('/')}{path}", token, q)
        if not data:
            break
        if not isinstance(data, list):
            raise RuntimeError(f"Expected list from {path}, got {type(data).__name__}")
        items.extend(data)
        if len(data) < MAX_PER_PAGE:
            break
        if page == max_pages:
            truncated = True
    return items, truncated


def slim_user(obj: Any) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    return {
        "id": obj.get("id"),
        "login": obj.get("login"),
        "name": obj.get("name"),
        "email": obj.get("email"),
        "html_url": obj.get("html_url"),
        "member_role": obj.get("member_role"),
        "permissions": obj.get("permissions"),
        "remark": obj.get("remark"),
        "contributions": obj.get("contributions"),
        "type": obj.get("type"),
    }


def slim_commit_list_item(item: dict[str, Any]) -> dict[str, Any]:
    commit = item.get("commit") if isinstance(item.get("commit"), dict) else {}
    author_git = commit.get("author") if isinstance(commit.get("author"), dict) else {}
    return {
        "sha": item.get("sha"),
        "html_url": item.get("html_url"),
        "message": commit.get("message") or "",
        "author_login": (item.get("author") or {}).get("login") if isinstance(item.get("author"), dict) else None,
        "author_name": (item.get("author") or {}).get("name") if isinstance(item.get("author"), dict) else author_git.get("name"),
        "author_email": author_git.get("email"),
        "authored_at": author_git.get("date"),
        "committer_login": (item.get("committer") or {}).get("login") if isinstance(item.get("committer"), dict) else None,
    }


def slim_commit_detail(item: dict[str, Any]) -> dict[str, Any]:
    base = slim_commit_list_item(item)
    files = []
    for f in item.get("files") or []:
        if not isinstance(f, dict):
            continue
        patch = f.get("patch") or ""
        files.append(
            {
                "filename": f.get("filename"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
                "changes": f.get("changes"),
                "truncated": bool(f.get("truncated")),
                "patch": patch[:PATCH_CHARS],
                "patch_omitted": len(patch) > PATCH_CHARS,
            }
        )
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    base.update(
        {
            "stats": {
                "additions": stats.get("additions"),
                "deletions": stats.get("deletions"),
                "total": stats.get("total"),
            },
            "files": files,
            "files_truncated": bool(item.get("truncated")),
        }
    )
    return base


def collect_errors(errors: list[dict[str, str]], step: str, err: Exception) -> None:
    errors.append({"step": step, "error": str(err)})


def main() -> int:
    args = parse_args()
    api = args.api_base.rstrip("/")
    owner = urllib.parse.quote(args.owner, safe="")
    repo = urllib.parse.quote(args.repo, safe="")
    errors: list[dict[str, str]] = []

    collaborators: list[Any] = []
    collab_truncated = False
    try:
        collaborators, collab_truncated = paginate(
            api,
            f"/repos/{owner}/{repo}/collaborators",
            args.token,
            {},
            args.max_pages,
        )
    except Exception as e:
        collect_errors(errors, "collaborators", e)

    contributors: list[Any] = []
    try:
        data = request_json(
            f"{api}/repos/{owner}/{repo}/contributors",
            args.token,
            {"type": "authors"},
        )
        contributors = data if isinstance(data, list) else []
    except Exception as e:
        collect_errors(errors, "contributors", e)

    commit_query = {
        "sha": args.sha,
        "since": args.since,
        "until": args.until,
        "author": args.author,
        "path": args.path,
    }
    commits_raw: list[Any] = []
    commits_truncated = False
    try:
        commits_raw, commits_truncated = paginate(
            api,
            f"/repos/{owner}/{repo}/commits",
            args.token,
            commit_query,
            args.max_pages,
        )
    except Exception as e:
        collect_errors(errors, "commits", e)

    commits = [slim_commit_list_item(c) for c in commits_raw if isinstance(c, dict)]
    details: list[dict[str, Any]] = []
    details_truncated = False
    limit = args.details_limit
    if limit < 0:
        limit = len(commits)
    to_hydrate = commits[:limit]
    if limit and len(commits) > limit:
        details_truncated = True
    for i, c in enumerate(to_hydrate):
        sha = c.get("sha")
        if not sha:
            continue
        try:
            raw = request_json(f"{api}/repos/{owner}/{repo}/commits/{urllib.parse.quote(sha, safe='')}", args.token)
            if isinstance(raw, dict):
                details.append(slim_commit_detail(raw))
        except Exception as e:
            collect_errors(errors, f"commit_detail:{sha}", e)
        if args.sleep and i + 1 < len(to_hydrate):
            time.sleep(args.sleep)

    payload = {
        "repo": {"owner": args.owner, "repo": args.repo, "api_base": api},
        "filters": {
            "sha": args.sha or None,
            "since": args.since or None,
            "until": args.until or None,
            "author": args.author or None,
            "path": args.path or None,
        },
        "auth": {"token_present": bool(args.token)},
        "collaborators": [slim_user(u) for u in collaborators if isinstance(u, dict)],
        "contributors": [slim_user(u) for u in contributors if isinstance(u, dict)],
        "commits": commits,
        "commit_details": details,
        "meta": {
            "collaborator_count": len(collaborators),
            "contributor_count": len(contributors),
            "commit_count": len(commits),
            "detail_count": len(details),
            "collaborators_truncated": collab_truncated,
            "commits_truncated": commits_truncated,
            "details_truncated": details_truncated,
            "max_pages": args.max_pages,
            "details_limit": args.details_limit,
        },
        "errors": errors,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        parent = os.path.dirname(os.path.abspath(args.out))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")
    return 0 if not any(e["step"] in ("commits",) for e in errors) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
