"""Local, namespace-scoped identity and repository inventory for Gitee diaries."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _gitee_http as gitee


def profile_path(namespace: str, profile_dir: str = "") -> Path:
    root = Path(profile_dir) if profile_dir else gitee.skill_root() / "profiles"
    digest = hashlib.sha256(namespace.strip().casefold().encode("utf-8")).hexdigest()[:20]
    return root / f"{digest}.json"


def load_store(namespace: str, profile_dir: str = "") -> dict[str, Any]:
    path = profile_path(namespace, profile_dir)
    if not path.exists():
        return {"schema_version": 1, "namespace": namespace, "profiles": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or str(data.get("namespace", "")).casefold() != namespace.casefold()
        or not isinstance(data.get("profiles"), list)
    ):
        raise ValueError(f"Invalid profile store: {path}")
    return data


def _search_fields(profile: dict[str, Any]) -> list[str]:
    identity = profile.get("identity") or {}
    fields = [profile.get("query"), identity.get("login"), identity.get("name"), identity.get("email")]
    fields.extend(profile.get("aliases") or [])
    return [str(value) for value in fields if value]


def find_profile(store: dict[str, Any], keyword: str, *, partial: bool = False) -> dict[str, Any] | None:
    needle = keyword.strip().casefold()
    if not needle:
        return None
    for profile in store.get("profiles", []):
        if not isinstance(profile, dict):
            continue
        fields = _search_fields(profile)
        if any((needle in value.casefold() if partial else needle == value.casefold()) for value in fields):
            return profile
    return None


def save_profile(profile: dict[str, Any], profile_dir: str = "") -> Path:
    namespace = profile["namespace"]
    store = load_store(namespace, profile_dir)
    profiles = store["profiles"]
    existing = find_profile(store, profile["query"])
    if existing is None:
        identity = profile.get("identity") or {}
        for field in ("login", "email"):
            value = identity.get(field)
            if value:
                existing = find_profile(store, str(value))
                if existing is not None:
                    break
    if existing is not None:
        profiles[profiles.index(existing)] = profile
    else:
        profiles.append(profile)
    path = profile_path(namespace, profile_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".profile-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(store, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.replace(temp_name, path)
        if os.name != "nt":
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def _scope_errors(errors: list[dict[str, str]], start: int, prefix: str) -> None:
    for item in errors[start:]:
        item["step"] = f"{prefix}:{item['step']}"


def scan_profile(
    api: str,
    namespace: str,
    person: str,
    token: str,
    max_pages: int,
    concurrency: int,
    namespace_type: str = "auto",
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Discover all matching repositories and branches, without fetching commits."""
    errors: list[dict[str, str]] = []
    repos, repos_truncated, kind = gitee.fetch_namespace_repos(
        api, namespace, token, max_pages, errors, namespace_type=namespace_type
    )

    def scan_repo_people(repo: dict[str, Any]) -> dict[str, Any]:
        local_errors: list[dict[str, str]] = []
        owner, name = repo.get("owner") or namespace, repo.get("name") or ""
        if not name:
            return {"repo": repo, "members": [], "contributors": [], "errors": local_errors,
                    "truncated": False}
        label = f"{owner}/{name}"
        owner_q, repo_q = gitee.repo_path(owner, name)
        start = len(local_errors)
        collaborators, members_truncated = gitee.fetch_collaborators(
            api, owner_q, repo_q, token, max_pages, local_errors
        )
        _scope_errors(local_errors, start, label)
        start = len(local_errors)
        contributors = gitee.fetch_contributors(api, owner_q, repo_q, token, local_errors)
        _scope_errors(local_errors, start, label)
        return {"repo": repo, "members": collaborators, "contributors": contributors,
                "errors": local_errors, "truncated": members_truncated}

    scanned_people = gitee.bounded_map(scan_repo_people, repos, max(1, concurrency))
    direct_users = [
        user for row in scanned_people for user in row["members"] + row["contributors"]
        if gitee.user_matches_person(person, user)
    ]
    confirmed_emails = {
        str(user.get("email")).strip().casefold()
        for user in direct_users if user.get("email")
    }

    def scan_repo_branches(row: dict[str, Any]) -> dict[str, Any]:
        repo = row["repo"]
        owner, name = repo.get("owner") or namespace, repo.get("name") or ""
        local_errors = row["errors"]

        def is_person(user: dict[str, Any]) -> bool:
            email = str(user.get("email") or "").strip().casefold()
            return gitee.user_matches_person(person, user) or bool(email and email in confirmed_emails)

        matched_members = [u for u in row["members"] if is_person(u)]
        matched_contributors = [u for u in row["contributors"] if is_person(u)]
        matched = matched_members + matched_contributors
        if not matched:
            return {"repository": None, "matched_users": [], "errors": local_errors,
                    "truncated": row["truncated"]}
        label = f"{owner}/{name}"
        owner_q, repo_q = gitee.repo_path(owner, name)
        start = len(local_errors)
        branches, branches_truncated = gitee.fetch_branches(
            api, owner_q, repo_q, token, max_pages, local_errors
        )
        _scope_errors(local_errors, start, label)
        member = matched_members[0] if matched_members else {}
        matched_emails = {str(u.get("email")).strip().casefold() for u in matched if u.get("email")}
        anchors = [u for u in direct_users if str(u.get("email") or "").strip().casefold() in matched_emails]
        return {
            "repository": {
                "owner": owner,
                "name": name,
                "full_name": repo.get("full_name") or label,
                "matched_as": "collaborator" if matched_members else "contributor",
                "member_role": member.get("member_role"),
                "permissions": member.get("permissions"),
                "identity_needles": gitee.identity_needles_for_person(person, anchors + matched),
                "branches": branches,
            },
            "matched_users": matched,
            "errors": local_errors,
            "truncated": row["truncated"] or branches_truncated,
        }

    scanned = gitee.bounded_map(scan_repo_branches, scanned_people, max(1, concurrency))
    matched_repos: list[dict[str, Any]] = []
    matched_users: list[dict[str, Any]] = []
    any_truncated = repos_truncated
    for row in scanned:
        errors.extend(row["errors"])
        any_truncated = any_truncated or row["truncated"]
        if row["repository"]:
            matched_repos.append(row["repository"])
            matched_users.extend(row["matched_users"])

    identity: dict[str, str | None] = {"login": None, "name": None, "email": None}
    for field in identity:
        for user in matched_users:
            if user.get(field):
                identity[field] = str(user[field])
                break
    aliases = gitee.identity_needles_for_person(person, matched_users)
    profile = {
        "namespace": namespace,
        "namespace_type": kind,
        "query": person,
        "identity": identity,
        "aliases": aliases,
        "repositories": matched_repos,
        "authorized_repositories": [
            repo for repo in matched_repos if repo["matched_as"] == "collaborator"
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "complete": bool(kind) and not errors and not any_truncated,
        "scan_meta": {
            "repo_count": len(repos),
            "matched_repo_count": len(matched_repos),
            "truncated": any_truncated,
        },
    }
    return profile, errors
