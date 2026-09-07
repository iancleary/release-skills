# Release Process

This repository uses Semantic Versioning with `v`-prefixed Git tags.

## Version Policy

The [`VERSION`](../VERSION) file is the source of truth. It contains the latest
released version without the `v` tag prefix.

- Patch releases fix behavior or documentation without changing a contract.
- Minor releases add compatible runner features, templates, or skill guidance.
- Major releases change a CLI, TOML, template, or skill-routing contract in an
  incompatible way.

The initial `0.0.0` value is an unreleased baseline. Use `--bump minor` for the
first `v0.1.0` release.

## Commands

Use the checked-in [`release.toml`](../release.toml) contract through the local
runner:

```sh
uv run scripts/release.py check --json
uv run scripts/release.py plan --json
uv run scripts/release.py run --dry-run --bump patch --json
uv run scripts/release.py run --apply --bump patch --json
```

The root runner contains the complete implementation. It does not load code or
validation rules from an installed skill directory or another checkout. The
skill package carries its own identical copy for use after installation.

Replace `patch` with `minor` or `major` when the change requires it. Use
`--version <version>` only for an exact version or prerelease. Do not pass both
`--bump` and `--version`.

## Release Contract

The runner:

1. Requires a clean worktree.
2. Confirms that the target tag does not exist locally or on `origin`.
3. Writes the next version to `VERSION`.
4. Runs `./scripts/check.sh` against the versioned tree.
5. Restores `VERSION` during a dry-run.
6. During apply, commits `VERSION`, creates an annotated tag, pushes the commit
   and tag, and creates the GitHub release.

GitHub generates release notes by default. Pass `--notes-file <path>` when a
release needs curated notes.

Checks are declared once in `[checks].commands` and enforced after VERSION is
prepared through `runner_protocol = "prepared-v1"`. Failed checks restore VERSION
before any Git mutation. Plan reports `ready: null`; pass its exact version,
target_commit and config_sha256 as --version, --expected-head and
--expected-config during execution. Read the
[shared contract](../skills/create-release-process/templates/release/README.md)
for verified GitHub publication recovery and consumer upgrade instructions.

Run apply only from a clean `main` branch with a configured `origin` and valid
GitHub CLI authentication. Apply is public and mutating. It requires an explicit
release request.

## Agent Routing

Use `create-release-process` to change this workflow. Use `release-runner` for
an ordinary release. The local repository contract overrides generic examples
in either skill.
