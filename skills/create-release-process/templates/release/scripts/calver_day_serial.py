#!/usr/bin/env python3
# Source: https://github.com/iancleary/release-skills
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Choose the next YYYYMMDD.0.N CalVer and run the release script."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview the release")
    mode.add_argument("--apply", action="store_true", help="Cut the release")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Repository root containing release.toml. Default: current directory.",
    )
    parser.add_argument(
        "--timezone",
        default=os.environ.get("RELEASE_TIMEZONE", "UTC"),
        help="Timezone for the date stamp. Default: RELEASE_TIMEZONE or UTC.",
    )
    parser.add_argument(
        "--tag-prefix",
        default=os.environ.get("RELEASE_TAG_PREFIX", ""),
        help="Tag prefix configured in release.toml. Default: RELEASE_TAG_PREFIX or empty.",
    )
    parser.add_argument(
        "--date",
        help="Override the date stamp as YYYYMMDD. Intended for tests and backfills.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not fetch origin tags before choosing the next serial.",
    )
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="Print the selected version without running the release runner.",
    )
    parser.add_argument(
        "runner_args",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed after release.py run. Prefix with -- if needed.",
    )
    return parser.parse_args()


def current_date(timezone: str) -> str:
    try:
        return datetime.now(ZoneInfo(timezone)).strftime("%Y%m%d")
    except ZoneInfoNotFoundError as exc:
        raise SystemExit(f"unknown timezone: {timezone}") from exc


def run_git(repo_path: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SystemExit(f"git {' '.join(args)} failed: {detail}")
    return result


def fetch_tags(repo_path: Path) -> None:
    run_git(repo_path, ["fetch", "origin", "--tags"])


def serial_from_tag(tag: str, tag_prefix: str, date_stamp: str) -> int | None:
    version = tag.removeprefix(tag_prefix)
    prefix = f"{date_stamp}.0."
    if not version.startswith(prefix):
        return None
    serial = version[len(prefix) :]
    if not serial.isdigit():
        return None
    return int(serial)


def next_version(repo_path: Path, tag_prefix: str, date_stamp: str) -> str:
    pattern = f"{tag_prefix}{date_stamp}.0.*"
    result = run_git(repo_path, ["tag", "--list", pattern])
    serials = [
        serial
        for tag in result.stdout.splitlines()
        if (serial := serial_from_tag(tag.strip(), tag_prefix, date_stamp)) is not None
    ]
    next_serial = max(serials) + 1 if serials else 0
    return f"{date_stamp}.0.{next_serial}"


def release_command(version: str, mode: str, extra_args: list[str]) -> list[str]:
    runner = shlex.split(
        os.environ.get("RELEASE_RUNNER", "uv run scripts/release.py")
    )
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    return [*runner, "run", mode, "--version", version, *extra_args]


def main() -> int:
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()
    if not args.no_fetch:
        fetch_tags(repo_path)
    date_stamp = args.date or current_date(args.timezone)
    version = next_version(repo_path, args.tag_prefix, date_stamp)
    if args.print_version:
        print(version)
        return 0
    mode = "--apply" if args.apply else "--dry-run"
    print(f"release version: {version}", file=sys.stderr)
    return subprocess.call(release_command(version, mode, args.runner_args), cwd=repo_path)


if __name__ == "__main__":
    raise SystemExit(main())
