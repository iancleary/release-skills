#!/bin/sh

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES="$ROOT/skills/create-release-process/templates/release"
CALVER_HELPER="$TEMPLATES/scripts/calver_day_serial.py"
RELEASE_RUNNER="$TEMPLATES/scripts/release.py"
LOCAL_RUNNER="$ROOT/scripts/release.py"
VALIDATOR="$ROOT/scripts/validate_skill.py"

fail() {
  echo "release-skills check failed: $*" >&2
  exit 1
}

command -v uv >/dev/null 2>&1 || fail "uv is required to run the Codex skill validator"
[ -x "$VALIDATOR" ] || fail "skill validator must be executable"
[ -x "$CALVER_HELPER" ] || fail "CalVer helper must be executable"
[ -x "$RELEASE_RUNNER" ] || fail "release runner must be executable"
[ -x "$LOCAL_RUNNER" ] || fail "local release runner must be executable"
cmp -s "$LOCAL_RUNNER" "$RELEASE_RUNNER" || fail "local and bundled release runners differ"
sh -n "$ROOT/scripts/check.sh"

for skill in create-release-process cut-release release-runner; do
  "$VALIDATOR" "$ROOT/skills/$skill"
done

uv run --no-project --python 3.11 python - "$ROOT" <<'PY'
from pathlib import Path
import sys
import tomllib

root = Path(sys.argv[1])
skills = root / "skills"
templates = skills / "create-release-process" / "templates" / "release"

with (root / "release.toml").open("rb") as stream:
    local_release = tomllib.load(stream)
version = (root / "VERSION").read_text().strip()
parts = version.split(".")
if len(parts) != 3 or not all(part.isdigit() for part in parts):
    raise SystemExit("VERSION must contain a SemVer core such as 1.2.3")
if local_release["release"].get("version_source") != "VERSION":
    raise SystemExit("local release contract must use VERSION")
if local_release["release"]["runner"][:4] != [
    "uv", "run", "scripts/release.py", "version-file-release"
]:
    raise SystemExit("local release contract must use the version-file runner")

for skill_dir in sorted(path for path in skills.iterdir() if path.is_dir()):
    text = (skill_dir / "SKILL.md").read_text()
    _, frontmatter, _ = text.split("---", 2)
    keys = {
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if line.strip()
    }
    if keys != {"name", "description"}:
        raise SystemExit(f"{skill_dir.name}: frontmatter must contain only name and description")

parsed = {}
for path in sorted(templates.glob("*.toml")):
    with path.open("rb") as stream:
        parsed[path.name] = tomllib.load(stream)

expected = {
    "cargo-calver-day-serial.release.toml",
    "cargo-semver-exact.release.toml",
    "cargo-semver-gitea.release.toml",
    "cargo-semver-github.release.toml",
    "semver-version-file-github.release.toml",
    "tag-only-github.release.toml",
}
if set(parsed) != expected:
    raise SystemExit("release template set does not match the repository contract")

def option_value(runner: list[str], option: str) -> str:
    try:
        return runner[runner.index(option) + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"missing runner option {option}") from exc

for name, document in parsed.items():
    if document["release"].get("runner_protocol") != "prepared-v1":
        raise SystemExit(f"{name}: must enforce prepared checks")
    if "--check" in document["release"]["runner"]:
        raise SystemExit(f"{name}: declare checks once in [checks]")
    if not name.startswith("cargo-"):
        continue
    runner = document["release"]["runner"]
    if runner[:4] != ["uv", "run", "scripts/release.py", "cargo-release"]:
        raise SystemExit(f"{name}: must use the bundled Python Cargo runner")
    if option_value(runner, "--version-source") != "Cargo.toml":
        raise SystemExit(f"{name}: must use Cargo.toml as the version source")
    if option_value(runner, "--lockfile") != "Cargo.lock":
        raise SystemExit(f"{name}: must include Cargo.lock")

calver = parsed["cargo-calver-day-serial.release.toml"]["release"]["runner"]
if option_value(calver, "--tag-prefix") != "":
    raise SystemExit("CalVer template must use unprefixed tags by default")

github = parsed["cargo-semver-github.release.toml"]["release"]["runner"]
if option_value(github, "--provider") != "github":
    raise SystemExit("GitHub template must select the GitHub provider")

gitea = parsed["cargo-semver-gitea.release.toml"]["release"]["runner"]
if option_value(gitea, "--provider") != "gitea":
    raise SystemExit("Gitea template must select the Gitea provider")

exact = parsed["cargo-semver-exact.release.toml"]["release"]["runner"]
if "--notes-required" not in exact:
    raise SystemExit("exact-version template must require release notes")

version_file = parsed["semver-version-file-github.release.toml"]["release"]
if version_file.get("version_source") != "VERSION":
    raise SystemExit("version-file template must use VERSION")
if version_file["runner"][:4] != [
    "uv", "run", "scripts/release.py", "version-file-release"
]:
    raise SystemExit("version-file template must use the bundled Python runner")
if option_value(version_file["runner"], "--provider") != "github":
    raise SystemExit("version-file template must select the GitHub provider")

tag_only = parsed["tag-only-github.release.toml"]["release"]
if tag_only["runner"][:4] != [
    "uv", "run", "scripts/release.py", "tag-release"
]:
    raise SystemExit("tag-only template must use the bundled Python runner")
if option_value(tag_only["runner"], "--provider") != "github":
    raise SystemExit("tag-only template must select the GitHub provider")

compile((templates / "scripts" / "calver_day_serial.py").read_text(),
        "calver_day_serial.py", "exec")
compile((templates / "scripts" / "release.py").read_text(), "release.py", "exec")
PY

uv run --no-project --python 3.11 python "$CALVER_HELPER" --help >/dev/null
"$RELEASE_RUNNER" --help >/dev/null
"$LOCAL_RUNNER" --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 \
  uv run --no-project --python 3.11 python -m unittest discover -s "$ROOT/tests"
git -C "$ROOT" diff --check

echo "release-skills checks passed"
