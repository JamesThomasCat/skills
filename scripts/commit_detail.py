#!/usr/bin/env python3
"""Fetch message + file diffs for one or more Gitee commit SHAs. No roster, no full history."""

from __future__ import annotations

import argparse
import sys

import _gitee_http as gitee


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch Gitee commit message and file diffs")
    gitee.add_common_args(p)
    p.add_argument(
        "--sha",
        action="append",
        required=True,
        help="Commit SHA (repeat for multiple). Short prefix is OK if unambiguous.",
    )
    args = p.parse_args()

    api = args.api_base.rstrip("/")
    owner_q, repo_q = gitee.repo_path(args.owner, args.repo)
    errors: list[dict[str, str]] = []
    details = []
    for sha in args.sha:
        for part in sha.split(","):
            part = part.strip()
            if not part:
                continue
            detail = gitee.fetch_commit_detail(api, owner_q, repo_q, args.token, part, errors)
            if detail:
                details.append(detail)

    gitee.write_json(
        gitee.envelope(
            args.owner,
            args.repo,
            api,
            args.token,
            {
                "shas": args.sha,
                "commit_details": details,
                "meta": {"detail_count": len(details)},
                "errors": errors,
            },
        ),
        args.out,
    )
    return 0 if details else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
