#!/usr/bin/env python3
"""Refresh and save one person's Gitee identity and repository inventory."""

from __future__ import annotations

import argparse
import sys

import _gitee_http as gitee
import _profiles as profiles


def main() -> int:
    p = argparse.ArgumentParser(description="Save a person's Gitee profile by namespace")
    gitee.add_auth_args(p)
    p.add_argument("--org", default="testdaily", help="Enterprise or organization path")
    p.add_argument("--namespace-type", choices=("auto", "enterprise", "org"), default="auto")
    p.add_argument("--person", required=True, help="Gitee login, name, or email")
    p.add_argument("--max-pages", type=int, default=50)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--http-timeout", type=float, default=10)
    p.add_argument("--profile-dir", default="", help="Profile storage directory (default: skill/profiles)")
    args = p.parse_args()
    if args.max_pages < 1:
        p.error("--max-pages must be >= 1")
    gitee.apply_token(args)
    gitee.configure_http(timeout=args.http_timeout)
    profile, errors = profiles.scan_profile(
        args.api_base.rstrip("/"), args.org, args.person, args.token, args.max_pages,
        max(1, args.concurrency), namespace_type=args.namespace_type,
    )
    path = None
    if profile.get("namespace_type"):
        path = profiles.save_profile(profile, args.profile_dir)
    gitee.write_json({"profile_path": str(path) if path else None, "profile": profile, "errors": errors}, args.out)
    return 0 if path else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
