#!/usr/bin/env python3
"""Shared Gitee Open API v5 helpers. Not a user-facing command."""

from __future__ import annotations

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


def add_common_args(parser) -> None:
    parser.add_argument("--owner", required=True, help="Namespace path (user/org/enterprise)")
    parser.add_argument("--repo", required=True, help="Repository path")
    parser.add_argument("--api-base", default=os.environ.get("GITEE_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--token", default=os.environ.get("GITEE_ACCESS_TOKEN", ""))
    parser.add_argument("--out", default="", help="Write JSON here; default stdout")


def repo_path(owner: str, repo: str) -> tuple[str, str]:
    return urllib.parse.quote(owner, safe=""), urllib.parse.quote(repo, safe="")


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
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    committer = item.get("committer") if isinstance(item.get("committer"), dict) else {}
    return {
        "sha": item.get("sha"),
        "html_url": item.get("html_url"),
        "message": commit.get("message") or "",
        "author_login": author.get("login"),
        "author_name": author.get("name") or author_git.get("name"),
        "author_email": author_git.get("email"),
        "authored_at": author_git.get("date"),
        "committer_login": committer.get("login"),
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


def fetch_collaborators(
    api: str, owner_q: str, repo_q: str, token: str, max_pages: int, errors: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], bool]:
    try:
        raw, truncated = paginate(api, f"/repos/{owner_q}/{repo_q}/collaborators", token, {}, max_pages)
        users = [u for u in (slim_user(x) for x in raw) if u]
        return users, truncated
    except Exception as e:
        collect_errors(errors, "collaborators", e)
        return [], False


def fetch_contributors(
    api: str, owner_q: str, repo_q: str, token: str, errors: list[dict[str, str]]
) -> list[dict[str, Any]]:
    try:
        data = request_json(
            f"{api}/repos/{owner_q}/{repo_q}/contributors",
            token,
            {"type": "authors"},
        )
        raw = data if isinstance(data, list) else []
        return [u for u in (slim_user(x) for x in raw) if u]
    except Exception as e:
        collect_errors(errors, "contributors", e)
        return []


def fetch_commits(
    api: str,
    owner_q: str,
    repo_q: str,
    token: str,
    query: dict[str, Any],
    max_pages: int,
    errors: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], bool]:
    try:
        raw, truncated = paginate(api, f"/repos/{owner_q}/{repo_q}/commits", token, query, max_pages)
        commits = [slim_commit_list_item(c) for c in raw if isinstance(c, dict)]
        return commits, truncated
    except Exception as e:
        collect_errors(errors, "commits", e)
        return [], False


def fetch_commit_detail(
    api: str, owner_q: str, repo_q: str, token: str, sha: str, errors: list[dict[str, str]]
) -> dict[str, Any] | None:
    try:
        raw = request_json(
            f"{api}/repos/{owner_q}/{repo_q}/commits/{urllib.parse.quote(sha, safe='')}",
            token,
        )
        if isinstance(raw, dict):
            return slim_commit_detail(raw)
    except Exception as e:
        collect_errors(errors, f"commit_detail:{sha}", e)
    return None


def fetch_commit_details(
    api: str,
    owner_q: str,
    repo_q: str,
    token: str,
    commits: list[dict[str, Any]],
    limit: int,
    sleep_s: float,
    errors: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], bool]:
    if limit < 0:
        limit = len(commits)
    to_hydrate = commits[:limit]
    truncated = bool(limit and len(commits) > limit)
    details: list[dict[str, Any]] = []
    for i, c in enumerate(to_hydrate):
        sha = c.get("sha")
        if not sha:
            continue
        detail = fetch_commit_detail(api, owner_q, repo_q, token, str(sha), errors)
        if detail:
            details.append(detail)
        if sleep_s and i + 1 < len(to_hydrate):
            time.sleep(sleep_s)
    return details, truncated


def envelope(owner: str, repo: str, api: str, token: str, extra: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "repo": {"owner": owner, "repo": repo, "api_base": api},
        "auth": {"token_present": bool(token)},
    }
    payload.update(extra)
    return payload


def write_json(payload: dict[str, Any], out: str) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        parent = os.path.dirname(os.path.abspath(out))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")
