#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Validate one skill directory without external packages or files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def scalar(value: str) -> str:
    value = value.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid quoted frontmatter value: {exc}") from exc
        if not isinstance(parsed, str):
            raise ValueError("frontmatter values must be strings")
        return parsed
    return value


def validate(skill_dir: Path) -> None:
    skill_file = skill_dir / "SKILL.md"
    try:
        text = skill_file.read_text()
    except OSError as exc:
        raise ValueError(f"failed to read {skill_file}: {exc}") from exc
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        _, frontmatter, body = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not closed") from exc

    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in fields:
            raise ValueError(f"duplicate frontmatter field: {key}")
        fields[key] = scalar(value)

    if set(fields) != {"name", "description"}:
        raise ValueError("frontmatter must contain only name and description")
    name = fields["name"]
    if not NAME.fullmatch(name) or len(name) > 64:
        raise ValueError("skill name must be hyphen-case and at most 64 characters")
    if name != skill_dir.name:
        raise ValueError(f"frontmatter name {name!r} must match directory {skill_dir.name!r}")
    description = fields["description"].strip()
    if not description or len(description) > 1024:
        raise ValueError("description must contain 1 to 1024 characters")
    if "<" in description or ">" in description:
        raise ValueError("description cannot contain angle brackets")
    if re.search(r"(?m)^\s*\[TODO:[^]]*]\s*$", body):
        raise ValueError("skill body contains an unfinished TODO placeholder")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    try:
        validate(args.skill_directory.resolve())
    except ValueError as exc:
        parser.exit(1, f"skill validation failed: {exc}\n")
    print("Skill is valid!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
