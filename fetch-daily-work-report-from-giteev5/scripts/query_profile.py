#!/usr/bin/env python3
"""Search locally saved Gitee profiles; makes no network requests."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import _gitee_http as gitee
import _profiles as profiles


def _matches(profile: dict[str, Any], keyword: str) -> bool:
    needle = keyword.casefold()
    fields = profiles._search_fields(profile)
    for repo in profile.get("repositories") or []:
        fields.extend(str(repo.get(key) or "") for key in ("name", "full_name", "owner"))
    return any(needle in value.casefold() for value in fields)


def main() -> int:
    p = argparse.ArgumentParser(description="Search saved Gitee user profiles")
    p.add_argument("--keyword", required=True, help="Part of a login, name, email, alias, or repository")
    p.add_argument("--org", default="testdaily", help="Namespace path (ignored with --all-namespaces)")
    p.add_argument("--all-namespaces", action="store_true")
    p.add_argument("--profile-dir", default="", help="Profile storage directory (default: skill/profiles)")
    p.add_argument("--out", default="", help="Write JSON here; default stdout")
    args = p.parse_args()
    keyword = args.keyword.strip()
    if not keyword:
        p.error("--keyword must not be empty")
    if args.all_namespaces:
        root = Path(args.profile_dir) if args.profile_dir else gitee.skill_root() / "profiles"
        paths = (
            sorted(path for path in root.glob("*.json") if re.fullmatch(r"[0-9a-f]{20}", path.stem))
            if root.exists() else []
        )
        stores = []
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            namespace = data.get("namespace") if isinstance(data, dict) else None
            if not isinstance(namespace, str):
                raise ValueError(f"Invalid profile store: {path}")
            stores.append(profiles.load_store(namespace, args.profile_dir))
    else:
        stores = [profiles.load_store(args.org, args.profile_dir)]
    matches = [profile for store in stores for profile in store["profiles"] if _matches(profile, keyword)]
    gitee.write_json({"keyword": keyword, "count": len(matches), "profiles": matches}, args.out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
