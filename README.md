# Release Skills

Reusable Codex skills for deterministic release workflows.

This repository is the canonical source for three complementary skills:

- [`create-release-process`](skills/create-release-process/SKILL.md) creates,
  audits, or repairs a checked-in release workflow.
- [`cut-release`](skills/cut-release/SKILL.md) executes an existing general
  repo-local release workflow.
- [`release-runner`](skills/release-runner/SKILL.md) executes a repository's
  `release.toml` contract through the bundled Python runner.

The `create-release-process` package also owns the standard-library Python
runner and reusable Cargo SemVer and CalVer templates under
[`templates/release`](skills/create-release-process/templates/release/README.md).
Target repositories run the copied script with `uv`; Forge is not required.

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
checks the CalVer helper, asserts the template contracts, and runs
`git diff --check`.

## Migration Provenance

The initial content was migrated from these source revisions:

- `create-release-process`, `release-runner`, and the templates used as the
  starting point for the local runner:
  `iancleary/forge` at `7027b9ecbf85dc6d06e05d2bf9bf351a851ef67c`
- `cut-release`:
  `iancleary/skills` at `affbb9a4401a2127728a84bba6ba589c55ee5d85`

See [`PLAN.md`](PLAN.md) for the full migration sequence and gate criteria.
