#!/usr/bin/env python3
"""List Gitee repo collaborators and contributors (type=authors). No commits."""

from __future__ import annotations

import argparse
import sys

import _gitee_http as gitee


def main() -> int:
    p = argparse.ArgumentParser(description="List Gitee repo members and contributors")
    gitee.add_common_args(p)
    p.add_argument("--max-pages", type=int, default=50, help="Safety cap for collaborator pages")
    args = p.parse_args()

    api = args.api_base.rstrip("/")
    owner_q, repo_q = gitee.repo_path(args.owner, args.repo)
    errors: list[dict[str, str]] = []

    collaborators, collab_truncated = gitee.fetch_collaborators(
        api, owner_q, repo_q, args.token, args.max_pages, errors
    )
    contributors = gitee.fetch_contributors(api, owner_q, repo_q, args.token, errors)

    gitee.write_json(
        gitee.envelope(
            args.owner,
            args.repo,
            api,
            args.token,
            {
                "collaborators": collaborators,
                "contributors": contributors,
                "meta": {
                    "collaborator_count": len(collaborators),
                    "contributor_count": len(contributors),
                    "collaborators_truncated": collab_truncated,
                    "max_pages": args.max_pages,
                },
                "errors": errors,
            },
        ),
        args.out,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        raise SystemExit(2)
