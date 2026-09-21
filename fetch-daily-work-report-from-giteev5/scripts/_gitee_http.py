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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

DEFAULT_API_BASE = "https://gitee.com/api/v5"
MAX_PER_PAGE = 100
PATCH_CHARS = 4000
TOKEN_ENV = "GITEE_ACCESS_TOKEN"
SKILL_SLUG = "fetch-daily-work-report-from-giteev5"
LEGACY_SKILL_SLUG = "gitee-auto"
SAVE_TARGETS = ("env", "dotenv", "session")
DEFAULT_HTTP_TIMEOUT = 30.0
http_timeout = DEFAULT_HTTP_TIMEOUT
_T = TypeVar("_T")
_R = TypeVar("_R")


def configure_http(*, timeout: float | None = None) -> None:
    """Process-wide HTTP timeout for request_json. Other entry scripts keep 30s until set."""
    global http_timeout
    if timeout is not None:
        http_timeout = float(timeout)


def bounded_map(fn: Callable[[_T], _R], items: Iterable[_T], workers: int = 1) -> list[_R]:
    """Apply fn to items, preserving order. workers<=1 stays on the calling thread."""
    seq = list(items)
    if not seq:
        return []
    if workers <= 1 or len(seq) == 1:
        return [fn(item) for item in seq]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, seq))


def default_skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def skill_root() -> Path:
    return default_skill_root()


def default_user_env_path() -> Path:
    return Path.home() / f".{SKILL_SLUG}" / "env"


def legacy_user_env_path() -> Path:
    return Path.home() / f".{LEGACY_SKILL_SLUG}" / "env"


def parse_env_file(path: str | Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return result
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            result[key] = val
    return result


def resolve_token(
    cli_token: str = "",
    environ: dict[str, str] | None = None,
    skill_root: Path | None = None,
    user_env_path: Path | None = None,
) -> tuple[str, str | None]:
    """CLI > process env > current user env > legacy user env > skill .env.

    Never reads API_KEY / ANTHROPIC_AUTH_TOKEN / ARK_*.
    """
    env = environ if environ is not None else os.environ
    root = Path(skill_root) if skill_root is not None else default_skill_root()
    user_paths = (
        [Path(user_env_path)]
        if user_env_path is not None
        else [default_user_env_path(), legacy_user_env_path()]
    )

    cli = (cli_token or "").strip()
    if cli:
        return cli, "cli"

    env_val = str(env.get(TOKEN_ENV) or "").strip()
    if env_val:
        return env_val, "environ"

    for user_path in user_paths:
        user_val = (parse_env_file(user_path).get(TOKEN_ENV) or "").strip()
        if user_val:
            return user_val, "user_env"

    dotenv_val = (parse_env_file(root / ".env").get(TOKEN_ENV) or "").strip()
    if dotenv_val:
        return dotenv_val, "dotenv"

    return "", None


def _line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None
    return stripped.partition("=")[0].strip()


def upsert_env_key(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    found = False
    out: list[str] = []
    for line in lines:
        if _line_key(line) == key:
            if not found:
                out.append(f"{key}={value}")
                found = True
            continue
        out.append(line)
    if not found:
        out.append(f"{key}={value}")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_windows_user_env(name: str, value: str) -> None:
    import ctypes
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)
    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    smto_abortifhung = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast, wm_settingchange, 0, "Environment", smto_abortifhung, 5000, None
    )


def save_token(
    target: str,
    token: str,
    skill_root: Path | None = None,
    user_env_path: Path | None = None,
    write_windows_user_env: bool = True,
) -> dict[str, Any]:
    cleaned = (token or "").strip()
    if not cleaned:
        raise ValueError("empty token")
    kind = (target or "").strip().lower()
    if kind not in SAVE_TARGETS:
        raise ValueError(f"unknown target: {target}")
    root = Path(skill_root) if skill_root is not None else default_skill_root()
    user_path = Path(user_env_path) if user_env_path is not None else default_user_env_path()

    if kind == "session":
        return {"ok": True, "target": "session", "path": None, "token_present": True}

    if kind == "dotenv":
        path = root / ".env"
        upsert_env_key(path, TOKEN_ENV, cleaned)
        return {"ok": True, "target": "dotenv", "path": str(path), "token_present": True}

    upsert_env_key(user_path, TOKEN_ENV, cleaned)
    if write_windows_user_env and os.name == "nt":
        try:
            _write_windows_user_env(TOKEN_ENV, cleaned)
        except OSError:
            pass
    return {"ok": True, "target": "env", "path": str(user_path), "token_present": True}


def apply_token(args: Any) -> None:
    token, source = resolve_token(cli_token=getattr(args, "token", "") or "")
    args.token = token
    args.token_source = source


def add_auth_args(parser) -> None:
    parser.add_argument("--api-base", default=os.environ.get("GITEE_API_BASE", DEFAULT_API_BASE))
    parser.add_argument(
        "--token",
        default="",
        help="Override token. Prefer GITEE_ACCESS_TOKEN env or files; avoid putting secrets on the CLI.",
    )
    parser.add_argument("--out", default="", help="Write JSON here; default stdout")


def add_common_args(parser) -> None:
    parser.add_argument("--owner", required=True, help="Namespace path (user/org/enterprise)")
    parser.add_argument("--repo", required=True, help="Repository path")
    add_auth_args(parser)


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
        "User-Agent": f"{SKILL_SLUG}/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(full, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
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


def day_bounds_iso(date_s: str) -> tuple[str, str]:
    """[start, end) for a calendar day in Asia/Shanghai (+08:00)."""
    from datetime import datetime, timedelta, timezone

    day = datetime.strptime(date_s.strip(), "%Y-%m-%d").date()
    tz = timezone(timedelta(hours=8))
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def person_matches(needle: str, *fields: Any) -> bool:
    n = (needle or "").strip().casefold()
    if not n:
        return False
    for raw in fields:
        if raw is None:
            continue
        v = str(raw).strip().casefold()
        if not v:
            continue
        if v == n:
            return True
        if len(n) >= 2 and (n in v or (len(v) >= 2 and v in n)):
            return True
        if "@" in v and v.split("@", 1)[0] == n:
            return True
    return False


def commit_matches_person(needle: str, commit: dict[str, Any]) -> bool:
    return person_matches(
        needle,
        commit.get("author_login"),
        commit.get("author_name"),
        commit.get("author_email"),
        commit.get("committer_login"),
    )


def user_matches_person(needle: str, user: dict[str, Any]) -> bool:
    return person_matches(needle, user.get("login"), user.get("name"), user.get("email"))


def identity_needles_for_person(person: str, users: list[dict[str, Any]]) -> list[str]:
    """Needles for commit matching: the query string plus matched users' login/name/email.

    Git author.name can change while author.email stays the same. Matching only the
    query name would drop those commits.
    """
    needles: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        s = str(raw).strip() if raw is not None else ""
        if not s:
            return
        key = s.casefold()
        if key in seen:
            return
        seen.add(key)
        needles.append(s)

    add(person)
    matched = [u for u in users if isinstance(u, dict) and user_matches_person(person, u)]
    emails: set[str] = set()
    for user in matched:
        add(user.get("login"))
        add(user.get("name"))
        add(user.get("email"))
        em = str(user.get("email") or "").strip().casefold()
        if em:
            emails.add(em)
    for user in users:
        if not isinstance(user, dict):
            continue
        em = str(user.get("email") or "").strip().casefold()
        if not em or em not in emails:
            continue
        add(user.get("login"))
        add(user.get("name"))
        add(user.get("email"))
    return needles


def commit_matches_any_person(needles: list[str], commit: dict[str, Any]) -> bool:
    return any(commit_matches_person(n, commit) for n in needles if n)


def _is_http_status(err: Exception, code: int) -> bool:
    return str(err).startswith(f"HTTP {code} ")


def _slim_repos(
    raw: list[Any], fallback_owner: str, *, repo_owner: str | None = None
) -> list[dict[str, Any]]:
    """Normalize repo list items.

    Enterprise list payloads often set owner.login to the creator (e.g. cuizhaoy),
    not the enterprise path. Subsequent /repos/{owner}/{repo} calls must use the
    enterprise path, so pass repo_owner=that path for enterprise listings.
    """
    repos: list[dict[str, Any]] = []
    forced = (repo_owner or "").strip()
    for item in raw:
        if not isinstance(item, dict):
            continue
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        name = item.get("path") or item.get("name") or ""
        owner_login = forced or (owner.get("login") or fallback_owner or "")
        if forced:
            full_name = f"{owner_login}/{name}" if name else owner_login
        else:
            full_name = item.get("full_name") or f"{owner_login}/{name}"
        repos.append(
            {
                "name": name,
                "full_name": full_name,
                "owner": owner_login,
                "html_url": item.get("html_url"),
                "private": item.get("private"),
                "default_branch": item.get("default_branch"),
            }
        )
    return repos


def fetch_namespace_repos(
    api: str,
    name: str,
    token: str,
    max_pages: int,
    errors: list[dict[str, str]],
    namespace_type: str = "auto",
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """List repos for an enterprise or org path.

    auto tries GET /enterprises/{name}/repos first (testdaily is an enterprise),
    then GET /orgs/{name}/repos only on HTTP 404. Other errors do not fall back.
    Enterprise listings force repo owner to the enterprise path so later
    /repos/{owner}/{repo} calls do not use creator logins such as cuizhaoy.
    """
    name_q = urllib.parse.quote(name, safe="")
    kind = (namespace_type or "auto").strip().lower()
    if kind not in ("auto", "enterprise", "org"):
        kind = "auto"
    ent_path = f"/enterprises/{name_q}/repos"
    org_path = f"/orgs/{name_q}/repos"

    def try_path(
        path: str, *, force_owner: str | None = None
    ) -> tuple[list[dict[str, Any]], bool] | Exception:
        try:
            raw, truncated = paginate(api, path, token, {"type": "all"}, max_pages)
            return _slim_repos(raw, name, repo_owner=force_owner), truncated
        except Exception as e:
            return e

    if kind == "org":
        result = try_path(org_path)
        if isinstance(result, Exception):
            collect_errors(errors, "org_repos", result)
            return [], False, None
        repos, truncated = result
        return repos, truncated, "org"

    result = try_path(ent_path, force_owner=name)
    if not isinstance(result, Exception):
        repos, truncated = result
        return repos, truncated, "enterprise"

    if kind == "enterprise" or not _is_http_status(result, 404):
        collect_errors(errors, "enterprise_repos", result)
        return [], False, None

    org_result = try_path(org_path)
    if isinstance(org_result, Exception):
        collect_errors(errors, "enterprise_repos", result)
        collect_errors(errors, "org_repos", org_result)
        return [], False, None
    repos, truncated = org_result
    return repos, truncated, "org"


def fetch_org_repos(
    api: str, org: str, token: str, max_pages: int, errors: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], bool]:
    repos, truncated, _ = fetch_namespace_repos(
        api, org, token, max_pages, errors, namespace_type="org"
    )
    return repos, truncated


def fetch_branches(
    api: str, owner_q: str, repo_q: str, token: str, max_pages: int, errors: list[dict[str, str]]
) -> tuple[list[str], bool]:
    try:
        raw, truncated = paginate(api, f"/repos/{owner_q}/{repo_q}/branches", token, {}, max_pages)
        names = [str(b.get("name")) for b in raw if isinstance(b, dict) and b.get("name")]
        return names, truncated
    except Exception as e:
        collect_errors(errors, "branches", e)
        return [], False


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


def envelope(
    owner: str,
    repo: str,
    api: str,
    token: str,
    extra: dict[str, Any],
    token_source: str | None = None,
) -> dict[str, Any]:
    payload = {
        "repo": {"owner": owner, "repo": repo, "api_base": api},
        "auth": {
            "token_present": bool(token),
            "token_source": token_source if token else None,
        },
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
