---
name: create-release-process
description: "Create, audit, or update a repo-local release process by discovering the repo's versioning, notes, validation, and publish requirements, then leaving a checked-in runner plus local agent instructions that future releases can execute deterministically."
---

# Create Release Process

Use this skill to establish or revise a repo-local release process. The goal is not to run one release by hand. The goal is to leave behind a deterministic local pattern that future agent runs can follow.

This is a portable skill. It should adapt to the target repo instead of imposing another repository's release policy.

## Use This When

- the user asks to create, define, audit, repair, or change a release workflow
- the repo does not have a deterministic release runner yet
- the repo's release process exists but does not match its current versioning, notes, validation, or publishing requirements
- ordinary release requests keep requiring reconstructed shell sequences

## Do Not Use This When

- the user is asking to cut or publish the next normal release and the repo already has a working release runner
- the task is only to query a current or next version through an existing read-only command
- the user is correcting an already-published release and needs explicit repair steps

For ordinary release execution, use `cut-release` after this workflow exists.

## Discovery

Decide the release process from repo evidence, not habit.

Inspect:

- local agent instructions: `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/release.md`
- package manager and version source: `Cargo.toml`, `pyproject.toml`, `package.json`, workspace manifests
- versioning scheme: SemVer, CalVer, date-based tags, or another documented repo-specific policy
- lockfiles: `Cargo.lock`, `uv.lock`, `pnpm-lock.yaml`, `package-lock.json`
- task runner: `justfile`, `Makefile`, package scripts, repo scripts
- checked-in automation: `.github/workflows/`, `.gitea/workflows/`, `.gitlab-ci.yml`, `.gitlab/`, or other committed CI/release workflow files
- validation path: local checkout checks first, such as tests, lint, type checks, builds, and release artifact generation, unless checked-in CI/release workflows define the release gate
- release notes source: generated changelog, curated markdown file, GitHub release notes, conventional commits, or repo-specific template
- publish mode: GitHub release, package registry publish, artifact upload, deploy, or manual handoff

Ask the user only when the repo evidence does not determine a safe policy.

## Tailoring Contract

The deployed skill supplies the pattern. The target repo supplies the contract.

Make the repo-local release process explicit about:

- versioning scheme and whether the next version can be inferred
- supported release intent arguments, such as `--bump patch|minor|major` for ordinary SemVer movement or `--version <v>` for exact versions when inference is unsafe
- release notes format and source, such as `--notes-file`, generated notes, or a checked-in template
- files the runner may mutate, including manifests and lockfiles
- validation commands that must pass before publishing
- whether validation is owned by local checkout checks, checked-in CI/release workflows, or both; prefer local checkout checks when no checked-in GitHub Actions, Gitea Actions, GitLab CI, or equivalent workflow exists
- lifecycle ordering, with tests and all required builds before irreversible publication and tag/release creation last when the platform permits it
- branch, clean-tree, tag, and remote requirements
- final public-facing action, such as `gh release create`, registry publish, deploy, or manual stop point
- dry-run behavior and read-only version query commands, when useful

## Implementation Pattern

Prefer the repo's existing task runner.

Prefer the repo's existing release command contract. When a repository uses the
bundled `release.toml` contract, use `uv run scripts/release.py` as the stable
agent-facing surface. Otherwise use the closest local convention, such as
`just cut-release`, `make release`, a package script, or a checked-in script.

For a new Python-backed `release.toml` workflow, start from the copyable
templates bundled with this skill:

- `templates/release/cargo-semver-github.release.toml` for ordinary GitHub Cargo SemVer releases
- `templates/release/cargo-semver-exact.release.toml` for exact versions, prereleases, build metadata, or required curated notes
- `templates/release/cargo-semver-gitea.release.toml` for Gitea or Forgejo releases through `tea`
- `templates/release/cargo-calver-day-serial.release.toml` plus `templates/release/scripts/calver_day_serial.py` for `YYYYMMDD.0.N` CalVer where the final numeric component starts at `0` each date
- `templates/release/semver-version-file-github.release.toml` for a repository
  that keeps SemVer in a plain `VERSION` file

Copy the closest template and `templates/release/scripts/release.py` into the
target repo. Edit the copies. Do not rebuild the same `release.toml` shape from
scratch when one of these templates is close.

When creating or updating the workflow:

- create or update a checked-in release runner
- make `--dry-run` available for previewing the mutating sequence
- prefer `uv run scripts/release.py run --dry-run --bump patch|minor|major --json` and `uv run scripts/release.py run --apply --bump patch|minor|major --json` when a SemVer repo can safely derive the exact next version from the current manifest
- keep `--bump` mutually exclusive with `--version`; use `--version <v>` for exact requested versions, prereleases, build metadata, CalVer, date tags, or repo-specific policy
- have the runner execute the repo's explicit local checkout checks before publication when no checked-in CI/release workflow owns that validation
- if checked-in GitHub Actions, Gitea Actions, GitLab CI, or equivalent workflows exist, make the runner invoke, monitor, or clearly defer to those workflows according to the repo's documented release gate
- add read-only version query commands when useful and expose them through
  `uv run scripts/release.py plan --json`
- route ordinary release requests through a `cut-release` execution skill when the repo wants agent routing
- update local agent instructions so future sessions know which skill and runner to use
- update release docs when the repo has a release document

Keep the runner narrow and auditable. Do not hide broad automation behind prompts.

## Output

Leave behind:

- the checked-in release runner or task recipe
- local instructions describing maintenance vs. execution
- release docs, if the repo has them
- a clear note on dry-run, versioning, notes, validation, and publishing behavior

## Safety

Release workflows are public-facing. Prefer inspect, dry-run, diff, then apply.

Do not publish, push, tag, or upload packages while creating or repairing the workflow unless the user explicitly asks for an actual release.
