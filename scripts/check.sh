#!/bin/sh

set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES="$ROOT/skills/create-release-process/templates/release"
CALVER_HELPER="$TEMPLATES/scripts/calver_day_serial.py"
RELEASE_RUNNER="$TEMPLATES/scripts/release.py"
VALIDATOR="${SKILL_VALIDATOR:-${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py}"

fail() {
  echo "release-skills check failed: $*" >&2
  exit 1
}

[ -f "$VALIDATOR" ] || fail "skill validator not found: $VALIDATOR"
command -v uv >/dev/null 2>&1 || fail "uv is required to run the Codex skill validator"
[ -x "$CALVER_HELPER" ] || fail "CalVer helper must be executable"
[ -x "$RELEASE_RUNNER" ] || fail "release runner must be executable"
sh -n "$ROOT/scripts/check.sh"

for skill in create-release-process cut-release release-runner; do
  uv run --no-project --with pyyaml "$VALIDATOR" "$ROOT/skills/$skill"
done

uv run --no-project --python 3.11 python - "$ROOT" <<'PY'
from pathlib import Path
import sys
import tomllib

root = Path(sys.argv[1])
skills = root / "skills"
templates = skills / "create-release-process" / "templates" / "release"

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
}
if set(parsed) != expected:
    raise SystemExit("release template set does not match the repository contract")

def option_value(runner: list[str], option: str) -> str:
    try:
        return runner[runner.index(option) + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"missing runner option {option}") from exc

for name, document in parsed.items():
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

compile((templates / "scripts" / "calver_day_serial.py").read_text(),
        "calver_day_serial.py", "exec")
compile((templates / "scripts" / "release.py").read_text(), "release.py", "exec")
PY

uv run --no-project --python 3.11 python "$CALVER_HELPER" --help >/dev/null
"$RELEASE_RUNNER" --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 \
  uv run --no-project --python 3.11 python -m unittest discover -s "$ROOT/tests"
git -C "$ROOT" diff --check

echo "release-skills checks passed"
