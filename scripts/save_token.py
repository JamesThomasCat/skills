#!/usr/bin/env python3
"""Persist a Gitee token. Reads the secret from env or stdin — not from printed output."""

from __future__ import annotations

import argparse
import json
import os
import sys

import _gitee_http as gitee


def _read_token(cli: str) -> str:
    token = (cli or "").strip() or (os.environ.get(gitee.TOKEN_ENV) or "").strip()
    if not token and not sys.stdin.isatty():
        token = sys.stdin.read().strip()
    return token


def main() -> int:
    p = argparse.ArgumentParser(description="Save GITEE_ACCESS_TOKEN to env file, skill .env, or session-only")
    p.add_argument("--target", required=True, choices=["env", "dotenv", "session"])
    p.add_argument(
        "--token",
        default="",
        help="Avoid this flag. Prefer GITEE_ACCESS_TOKEN in the environment or stdin.",
    )
    args = p.parse_args()
    try:
        result = gitee.save_token(args.target, _read_token(args.token))
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
