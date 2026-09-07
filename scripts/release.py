#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Execute a checked-in release.toml contract."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


class ReleaseError(RuntimeError):
    """A release contract or command failed."""


@dataclass
class CommandResult:
    command: list[str]
    ok: bool
    exit_status: int | None
    stdout: str
    stderr: str


def command(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ReleaseError(f"{label} must be a non-empty string array")
    if not all(isinstance(part, str) for part in value) or not value[0].strip():
        raise ReleaseError(f"{label} must be a non-empty string array")
    if value[0].startswith("builtin:"):
        raise ReleaseError(f"{label} uses unsupported legacy command {value[0]}")
    return list(value)


def repo_file(repo: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ReleaseError(f"{label} must stay inside the repository: {value}") from exc
    return resolved


def load_config(repo: Path, config_name: str) -> tuple[Path, dict[str, Any]]:
    config_path = repo_file(repo, config_name, "config path")
    try:
        with config_path.open("rb") as stream:
            config = tomllib.load(stream)
    except OSError as exc:
        raise ReleaseError(f"failed to read {config_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ReleaseError(f"failed to parse {config_path}: {exc}") from exc

    release = config.get("release")
    checks = config.get("checks", {})
    if not isinstance(release, dict):
        raise ReleaseError("release.toml requires [release]")
    if not isinstance(checks, dict):
        raise ReleaseError("release.toml [checks] must be a table")
    if not isinstance(release.get("name"), str) or not release["name"].strip():
        raise ReleaseError("release.toml requires release.name")
    command(release.get("runner"), "release.runner")
    for key in ("current_version_command", "next_version_command"):
        if key in release:
            command(release[key], f"release.{key}")
    dry_run_args = release.get("dry_run_args", [])
    if not isinstance(dry_run_args, list) or not all(
        isinstance(part, str) and part.strip() for part in dry_run_args
    ):
        raise ReleaseError("release.dry_run_args must be a string array")
    configured_checks = checks.get("commands", [])
    if not isinstance(configured_checks, list):
        raise ReleaseError("checks.commands must be an array of command arrays")
    for index, item in enumerate(configured_checks):
        command(item, f"checks.commands[{index}]")
    return config_path, config


def run_command(repo: Path, argv: Sequence[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            list(argv), cwd=repo, check=False, text=True, capture_output=True
        )
    except OSError as exc:
        raise ReleaseError(f"failed to run {' '.join(argv)}: {exc}") from exc
    return CommandResult(
        command=list(argv),
        ok=completed.returncode == 0,
        exit_status=completed.returncode,
        stdout=completed.stdout[-8000:],
        stderr=completed.stderr[-8000:],
    )


def require_success(result: CommandResult) -> str:
    if not result.ok:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise ReleaseError(f"command failed ({' '.join(result.command)}): {detail}")
    return result.stdout.strip()


def base_result(
    action: str,
    mode: str,
    repo: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    release = config["release"]
    return {
        "command": action,
        "mode": mode,
        "config_path": str(config_path),
        "repo_path": str(repo),
        "name": release["name"],
        "version_source": release.get("version_source"),
        "current_version": None,
        "next_version": None,
        "publish": release.get("publish", True),
        "changelog": release.get("changelog"),
        "notes_file": release.get("notes_file"),
        "runner": list(release["runner"]),
        "checks": [],
        "ready": True,
        "executed": False,
        "exit_status": None,
        "runner_stdout": None,
        "runner_stderr": None,
    }


def execute_check(repo: Path, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    result = base_result("check", "check", repo, config_path, config)
    checks = [
        run_command(repo, command(item, f"checks.commands[{index}]"))
        for index, item in enumerate(config.get("checks", {}).get("commands", []))
    ]
    result["checks"] = [item.__dict__ for item in checks]
    result["ready"] = all(item.ok for item in checks)
    return result


def optional_query(repo: Path, release: dict[str, Any], key: str) -> str | None:
    value = release.get(key)
    if value is None:
        return None
    return require_success(run_command(repo, command(value, f"release.{key}")))


def execute_plan(repo: Path, config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    result = base_result("plan", "plan", repo, config_path, config)
    result["current_version"] = optional_query(
        repo, config["release"], "current_version_command"
    )
    result["next_version"] = optional_query(
        repo, config["release"], "next_version_command"
    )
    return result


def execute_run(
    repo: Path,
    config_path: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    release = config["release"]
    runner = command(release["runner"], "release.runner")
    if not args.apply:
        dry_run_args = release.get("dry_run_args", [])
        if not dry_run_args:
            raise ReleaseError("release.dry_run_args is required for dry-run mode")
        runner.extend(dry_run_args)
    if args.version:
        runner.extend(["--version", args.version])
    if args.bump:
        runner.extend(["--bump", args.bump])
    if args.notes_file:
        runner.extend(["--notes-file", args.notes_file])
    if args.not_latest:
        runner.append("--not-latest")

    command_result = run_command(repo, runner)
    require_success(command_result)
    result = base_result(
        "run", "apply" if args.apply else "dry_run", repo, config_path, config
    )
    result["runner"] = runner
    result["executed"] = True
    result["exit_status"] = command_result.exit_status
    result["runner_stdout"] = command_result.stdout
    result["runner_stderr"] = command_result.stderr
    return result


SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def validate_semver(version: str) -> None:
    if not SEMVER.fullmatch(version):
        raise ReleaseError("--version must be a SemVer value like 1.2.3")


def release_tag(repo: Path, version: str, tag_prefix: str) -> str:
    if not version or version != version.strip():
        raise ReleaseError("--version must be a non-empty value without surrounding whitespace")
    tag = f"{tag_prefix}{version}"
    result = run_command(repo, ["git", "check-ref-format", f"refs/tags/{tag}"])
    if not result.ok:
        raise ReleaseError(f"version and tag prefix produce an invalid Git tag: {tag}")
    return tag


def bump_semver(version: str, bump: str) -> str:
    if "-" in version or "+" in version:
        raise ReleaseError(
            "--bump requires a stable current version; pass --version for a prerelease"
        )
    validate_semver(version)
    major, minor, patch = (int(part) for part in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def cargo_package(repo: Path, source: str) -> tuple[str, str]:
    path = repo_file(repo, source, "version source")
    try:
        with path.open("rb") as stream:
            package = tomllib.load(stream)["package"]
        name, version = package["name"], package["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError(f"failed to read package name and version from {path}") from exc
    if not isinstance(name, str) or not isinstance(version, str):
        raise ReleaseError(f"{path} package name and version must be strings")
    return name, version


def rewrite_manifest(path: Path, version: str) -> None:
    body = path.read_text()
    section = None
    changed = False
    output = []
    for line in body.splitlines(keepends=True):
        match = re.match(r"\s*\[([^]]+)]\s*$", line)
        if match:
            section = match.group(1)
        if section == "package" and re.match(r"\s*version\s*=", line) and not changed:
            ending = "\n" if line.endswith("\n") else ""
            indent = line[: len(line) - len(line.lstrip())]
            line = f'{indent}version = "{version}"{ending}'
            changed = True
        output.append(line)
    if not changed:
        raise ReleaseError(f"{path} does not declare package.version")
    path.write_text("".join(output))


def rewrite_lock(path: Path, package_name: str, version: str) -> None:
    body = path.read_text()
    blocks = body.split("[[package]]")
    changed = False
    for index in range(1, len(blocks)):
        block = blocks[index]
        if re.search(rf'^name = "{re.escape(package_name)}"$', block, re.MULTILINE):
            block, count = re.subn(
                r'^version = "[^"]+"$',
                f'version = "{version}"',
                block,
                count=1,
                flags=re.MULTILINE,
            )
            if count:
                blocks[index] = block
                changed = True
                break
    if not changed:
        raise ReleaseError(f"package {package_name} not found in {path}")
    path.write_text("[[package]]".join(blocks))


def git(repo: Path, *args: str) -> str:
    return require_success(run_command(repo, ["git", *args]))


def ensure_tag_absent(repo: Path, tag: str) -> None:
    if git(repo, "tag", "--list", tag):
        raise ReleaseError(f"local tag already exists: {tag}")
    if git(repo, "ls-remote", "--tags", "origin", f"refs/tags/{tag}"):
        raise ReleaseError(f"remote tag already exists: {tag}")


def cargo_current_version(repo: Path, args: argparse.Namespace) -> int:
    _, version = cargo_package(repo, args.version_source)
    print(version)
    return 0


def read_version_file(repo: Path, value: str) -> tuple[Path, str]:
    path = repo_file(repo, value, "version file")
    try:
        version = path.read_text().strip()
    except OSError as exc:
        raise ReleaseError(f"failed to read {path}: {exc}") from exc
    validate_semver(version)
    return path, version


def version_file_current(repo: Path, args: argparse.Namespace) -> int:
    _, version = read_version_file(repo, args.version_file)
    print(version)
    return 0


def prepare_release(
    repo: Path, current: str, args: argparse.Namespace
) -> tuple[str, str, Path | None]:
    if bool(args.version) == bool(args.bump):
        raise ReleaseError("exactly one of --version or --bump is required")
    version = args.version or bump_semver(current, args.bump)
    validate_semver(version)
    if version == current:
        raise ReleaseError(f"target version matches current version ({version})")
    tag, notes_path = prepare_tag(repo, version, args)
    return version, tag, notes_path


def prepare_tag(
    repo: Path, version: str, args: argparse.Namespace
) -> tuple[str, Path | None]:
    tag = release_tag(repo, version, args.tag_prefix)
    notes_path = repo_file(repo, args.notes_file, "notes file") if args.notes_file else None
    if notes_path and not notes_path.is_file():
        raise ReleaseError(f"notes file not found: {args.notes_file}")
    if args.notes_required and not args.dry_run and notes_path is None:
        raise ReleaseError("--notes-file is required for a real release")
    if git(repo, "status", "--short"):
        raise ReleaseError("working tree must be clean before cutting a release")
    if not args.dry_run:
        branch = git(repo, "branch", "--show-current")
        if branch != args.branch:
            raise ReleaseError(
                f"real releases must run from {args.branch}; current branch is {branch}"
            )
        auth = ["gh", "auth", "status"] if args.provider == "github" else ["tea", "login", "list"]
        require_success(run_command(repo, auth))
    ensure_tag_absent(repo, tag)
    return tag, notes_path


def publish_release(
    repo: Path, args: argparse.Namespace, tag: str, notes_path: Path | None
) -> None:
    if args.provider == "github":
        publish = ["gh", "release", "create", tag, "--verify-tag"]
        publish += ["--notes-file", str(notes_path)] if notes_path else ["--generate-notes"]
        if args.not_latest:
            publish.append("--latest=false")
    else:
        if args.not_latest:
            raise ReleaseError("--not-latest is not supported by the Gitea provider")
        publish = ["tea", "releases", "create", "--tag", tag, "--title", tag]
        publish += ["--note-file", str(notes_path)] if notes_path else ["--note", f"Release {tag}"]
    require_success(run_command(repo, publish))


def commit_tag_push(repo: Path, paths: Sequence[Path], tag: str) -> None:
    git(repo, "add", *(str(path.relative_to(repo)) for path in paths))
    git(repo, "commit", "-m", f"chore: release {tag}")
    git(repo, "tag", "-a", tag, "-m", f"Release {tag}")
    git(repo, "push", "origin", "HEAD")
    git(repo, "push", "origin", tag)


def version_file_release(repo: Path, args: argparse.Namespace) -> int:
    version_path, current = read_version_file(repo, args.version_file)
    version, tag, notes_path = prepare_release(repo, current, args)
    original = version_path.read_bytes()
    try:
        version_path.write_text(f"{version}\n")
        for check_text in args.check:
            require_success(run_command(repo, shlex.split(check_text)))
        if args.dry_run:
            print(f"Dry run succeeded for {tag}.")
            return 0

        commit_tag_push(repo, [version_path], tag)
        publish_release(repo, args, tag, notes_path)
        print(f"release ready: {tag}")
        return 0
    finally:
        if args.dry_run:
            version_path.write_bytes(original)


def tag_release(repo: Path, args: argparse.Namespace) -> int:
    if not args.version:
        raise ReleaseError("--version is required for a tag-only release")
    tag, notes_path = prepare_tag(repo, args.version, args)

    for check_text in args.check:
        require_success(run_command(repo, shlex.split(check_text)))
    if args.dry_run:
        print(f"Dry run succeeded for {tag}.")
        return 0

    git(repo, "tag", "-a", tag, "-m", f"Release {tag}")
    git(repo, "push", "origin", tag)
    publish_release(repo, args, tag, notes_path)
    print(f"release ready: {tag}")
    return 0


def cargo_release(repo: Path, args: argparse.Namespace) -> int:
    package_name, current = cargo_package(repo, args.version_source)
    version, tag, notes_path = prepare_release(repo, current, args)

    targets = [repo_file(repo, item, "version target") for item in args.version_target]
    lockfiles = [repo_file(repo, item, "lockfile") for item in args.lockfile]
    backups = {path: path.read_bytes() for path in {*targets, *lockfiles}}
    try:
        for target in targets:
            rewrite_manifest(target, version)
        for lockfile in lockfiles:
            rewrite_lock(lockfile, package_name, version)
        for check_text in args.check:
            require_success(run_command(repo, shlex.split(check_text)))
        if args.dry_run:
            print(f"Dry run succeeded for {package_name} {tag}.")
            return 0

        commit_tag_push(repo, list(backups), tag)
        publish_release(repo, args, tag, notes_path)
        print(f"release ready: {tag}")
        return 0
    finally:
        if args.dry_run:
            for path, body in backups.items():
                path.write_bytes(body)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-path", default=".")
    parser.add_argument("--config", default="release.toml")
    parser.add_argument("--json", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("check", "plan"):
        add_common(subparsers.add_parser(action))
    run_parser = subparsers.add_parser("run")
    add_common(run_parser)
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    intent = run_parser.add_mutually_exclusive_group()
    intent.add_argument("--version")
    intent.add_argument("--bump", choices=("major", "minor", "patch"))
    run_parser.add_argument("--notes-file")
    run_parser.add_argument("--not-latest", action="store_true")

    current = subparsers.add_parser("cargo-current-version")
    current.add_argument("--repo-path", default=".")
    current.add_argument("--version-source", default="Cargo.toml")

    cargo = subparsers.add_parser("cargo-release")
    cargo.add_argument("--repo-path", default=".")
    cargo.add_argument("--provider", choices=("github", "gitea"), default="github")
    cargo.add_argument("--version-source", default="Cargo.toml")
    cargo.add_argument("--version-target", action="append", default=[])
    cargo.add_argument("--lockfile", action="append", default=[])
    cargo.add_argument("--tag-prefix", default="v")
    cargo.add_argument("--branch", default="main")
    cargo.add_argument("--check", action="append", default=[])
    cargo.add_argument("--notes-required", action="store_true")
    cargo.add_argument("--version")
    cargo.add_argument("--bump", choices=("major", "minor", "patch"))
    cargo.add_argument("--notes-file")
    cargo.add_argument("--not-latest", action="store_true")
    cargo.add_argument("--dry-run", action="store_true")

    version_current = subparsers.add_parser("version-file-current")
    version_current.add_argument("--repo-path", default=".")
    version_current.add_argument("--version-file", default="VERSION")

    version_release = subparsers.add_parser("version-file-release")
    version_release.add_argument("--repo-path", default=".")
    version_release.add_argument("--provider", choices=("github", "gitea"), default="github")
    version_release.add_argument("--version-file", default="VERSION")
    version_release.add_argument("--tag-prefix", default="v")
    version_release.add_argument("--branch", default="main")
    version_release.add_argument("--check", action="append", default=[])
    version_release.add_argument("--notes-required", action="store_true")
    version_release.add_argument("--version")
    version_release.add_argument("--bump", choices=("major", "minor", "patch"))
    version_release.add_argument("--notes-file")
    version_release.add_argument("--not-latest", action="store_true")
    version_release.add_argument("--dry-run", action="store_true")

    tag_only = subparsers.add_parser("tag-release")
    tag_only.add_argument("--repo-path", default=".")
    tag_only.add_argument("--provider", choices=("github", "gitea"), default="github")
    tag_only.add_argument("--tag-prefix", default="")
    tag_only.add_argument("--branch", default="main")
    tag_only.add_argument("--check", action="append", default=[])
    tag_only.add_argument("--notes-required", action="store_true")
    tag_only.add_argument("--version")
    tag_only.add_argument("--notes-file")
    tag_only.add_argument("--not-latest", action="store_true")
    tag_only.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"{result['name']}: {result['mode']} ready={str(result['ready']).lower()}")


def main() -> int:
    args = parse_args()
    repo = Path(args.repo_path).resolve()
    try:
        if args.action == "cargo-current-version":
            return cargo_current_version(repo, args)
        if args.action == "version-file-current":
            return version_file_current(repo, args)
        if args.action == "version-file-release":
            return version_file_release(repo, args)
        if args.action == "tag-release":
            return tag_release(repo, args)
        if args.action == "cargo-release":
            if not args.version_target:
                args.version_target = [args.version_source]
            return cargo_release(repo, args)
        config_path, config = load_config(repo, args.config)
        if args.action == "check":
            result = execute_check(repo, config_path, config)
        elif args.action == "plan":
            result = execute_plan(repo, config_path, config)
        else:
            result = execute_run(repo, config_path, config, args)
        print_result(result, args.json)
        return 0 if result["ready"] else 1
    except ReleaseError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        else:
            print(f"release failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
