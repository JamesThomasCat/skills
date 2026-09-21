#!/usr/bin/env python3
"""Validate internal links, stable control IDs, UI metadata, and eval fixtures."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
CONTROL_RE = re.compile(r"\[([A-Z]{2,4}-(?:G)?\d{2})\]")
LINK_RE = re.compile(r"\]\(([^)#]+\.md)(?:#[^)]+)?\)")
PHASE_PREFIXES = {
    "01-initiation.md": "INI",
    "02-requirements.md": "REQ",
    "03-design.md": "DES",
    "04-implementation.md": "IMP",
    "05-verification.md": "VER",
    "06-release.md": "REL",
    "07-operations.md": "OPS",
    "08-retirement.md": "RET",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_markdown(errors: list[str]) -> None:
    ids: list[str] = []
    for path in SKILL_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        ids.extend(CONTROL_RE.findall(text))
        for target in LINK_RE.findall(text):
            resolved = (path.parent / target).resolve()
            if not resolved.is_file():
                fail(errors, f"broken link in {path.relative_to(SKILL_DIR)}: {target}")

    duplicates = [control_id for control_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        fail(errors, "duplicate control IDs: " + ", ".join(sorted(duplicates)))

    references = SKILL_DIR / "references" / "lifecycle"
    for filename, prefix in PHASE_PREFIXES.items():
        text = (references / filename).read_text(encoding="utf-8")
        phase_ids = CONTROL_RE.findall(text)
        if not phase_ids:
            fail(errors, f"no control IDs found in {filename}")
        wrong = [item for item in phase_ids if not item.startswith(prefix + "-")]
        if wrong:
            fail(errors, f"unexpected control prefix in {filename}: {', '.join(wrong)}")
        if not any(item.startswith(prefix + "-G") for item in phase_ids):
            fail(errors, f"no gate control ID found in {filename}")


def validate_interface(errors: list[str]) -> None:
    text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "$software-development-instruction-rules" not in text:
        fail(errors, "agents/openai.yaml default_prompt must mention the skill explicitly")


def validate_evals(errors: list[str]) -> None:
    path = SKILL_DIR / "evals" / "scenarios.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, f"invalid eval scenarios: {exc}")
        return

    scenarios = data.get("scenarios", [])
    scenario_ids = [scenario.get("id") for scenario in scenarios]
    if len(scenarios) < 8:
        fail(errors, "expected at least eight behavioral eval scenarios")
    if len(scenario_ids) != len(set(scenario_ids)):
        fail(errors, "duplicate eval scenario IDs")
    for scenario in scenarios:
        for key in ("id", "prompt", "expected_behaviors", "forbidden_behaviors"):
            if not scenario.get(key):
                fail(errors, f"eval scenario missing {key}: {scenario.get('id', '<unknown>')}")


def main() -> int:
    errors: list[str] = []
    validate_markdown(errors)
    validate_interface(errors)
    validate_evals(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Skill content validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
