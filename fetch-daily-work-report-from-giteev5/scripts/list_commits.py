#!/usr/bin/env python3
"""List Gitee commits (message only). Does not fetch file diffs."""

from __future__ import annotations

import argparse
import sys

import _gitee_http as gitee


def main() -> int:
    p = argparse.ArgumentParser(description="List Gitee repo commits without diffs")
    gitee.add_common_args(p)
    p.add_argument("--sha", default="", help="Branch name or starting SHA")
    p.add_argument("--since", default="", help="ISO 8601 start time")
    p.add_argument("--until", default="", help="ISO 8601 end time")
    p.add_argument("--author", default="", help="Filter by email or login")
    p.add_argument("--path", default="", help="Only commits touching this file path")
    p.add_argument("--max-pages", type=int, default=50, help="Safety cap; 100 commits per page")
    args = p.parse_args()
    gitee.apply_token(args)

    api = args.api_base.rstrip("/")
    owner_q, repo_q = gitee.repo_path(args.owner, args.repo)
    errors: list[dict[str, str]] = []
    query = {
        "sha": args.sha,
        "since": args.since,
        "until": args.until,
        "author": args.author,
        "path": args.path,
    }
    commits, truncated = gitee.fetch_commits(api, owner_q, repo_q, args.token, query, args.max_pages, errors)

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
                "commits": commits,
                "meta": {
                    "commit_count": len(commits),
                    "commits_truncated": truncated,
                    "max_pages": args.max_pages,
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
