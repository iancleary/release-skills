# Release Skills

Reusable Codex skills for deterministic release workflows.

## Prompt for Your Agent

Give your agent this repository URL and the following prompt. "This repo"
means the consuming project where you want a release workflow.

> Use https://github.com/iancleary/release-skills to set up or execute this
> repo's release workflow. Preserve the repo's version policy—SemVer, CalVer,
> or another documented scheme. Use `create-release-process` for setup or
> maintenance, `release-runner` for the bundled Python `release.toml` workflow,
> and `cut-release` for another existing runner. Keep repository policy in
> TOML and small helpers, pin the unchanged shared runner by commit and
> checksum, and verify checks, planning, and dry-run before publishing.
> Publish only when explicitly requested. Install skills project-locally if
> needed; do not install globally.

Agents arriving from the URL should read the relevant linked `SKILL.md`
below before acting. See [install.md](install.md) only if installation is
needed. A repository URL alone does not authorize publication.

## Skills

This repository is the canonical source for three complementary skills:

- [`create-release-process`](skills/create-release-process/SKILL.md) creates,
  audits, or repairs a checked-in release workflow.
- [`cut-release`](skills/cut-release/SKILL.md) executes an existing general
  repo-local release workflow.
- [`release-runner`](skills/release-runner/SKILL.md) executes a repository's
  `release.toml` contract through the bundled Python runner.

The `create-release-process` package also owns the standard-library Python
runner and reusable Cargo, version-file SemVer, CalVer, and arbitrary tag-only
templates under
[`templates/release`](skills/create-release-process/templates/release/README.md).
Target repositories run the copied script with `uv`; Forge is not required.

This repository uses SemVer for its own releases. Consumer repositories keep
their own version policy. Exact consumer versions are opaque Git-tag-safe
strings; only runners that offer `--bump major|minor|patch` require SemVer.

The [shared execution contract](skills/create-release-process/templates/release/README.md)
defines enforced checks, descriptive plans, consumer version validation, GitHub
publication recovery, and checksums for vendored runners. Consumer policy stays
in TOML and small helpers so the runner can be updated without local edits.

## Install

See [`install.md`](install.md) for the agent-driven installation contract. To
install directly in the current repository, run:

```sh
npx skills add iancleary/release-skills
```

Add `-g` for a user-global installation.

## Validate

```sh
./scripts/check.sh
```

The check validates all three skill packages, parses every TOML template,
checks the CalVer helper, asserts the template contracts, verifies both
checked-in runner copies, and runs `git diff --check`. Validation uses only
files in this repository and Python's standard library.

## Releases

This repository uses Semantic Versioning. The current version lives in
[`VERSION`](VERSION), and the release contract lives in
[`release.toml`](release.toml).

Use the repository's own skills and runner:

```sh
uv run scripts/release.py check --json
uv run scripts/release.py plan --json
uv run scripts/release.py run --dry-run --bump patch --json
```

See [`docs/release.md`](docs/release.md) for version policy and the explicit
publish path.

## Migration Provenance

The initial content was migrated from these source revisions:

- `create-release-process`, `release-runner`, and the templates used as the
  starting point for the local runner:
  `iancleary/forge` at `7027b9ecbf85dc6d06e05d2bf9bf351a851ef67c`
- `cut-release`:
  `iancleary/skills` at `affbb9a4401a2127728a84bba6ba589c55ee5d85`

See [`PLAN.md`](PLAN.md) for the full migration sequence and gate criteria.
