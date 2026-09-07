# Release Skills Migration Plan

## Goal

Make `iancleary/release-skills` the canonical home for reusable release workflow
skills, a portable Python release runner, and release templates.

Preserve these installed skill names and their current behavior:

- `create-release-process`
- `release-runner`
- `cut-release`

Do not require the Forge CLI to install, validate, or use these skills. Forge can
retain its existing release command for compatibility and its own workflow.

## Repository Boundary

`iancleary/release-skills` owns:

- instructions for creating and maintaining deterministic release workflows
- instructions for executing an existing release workflow
- a standard-library Python runner for the portable `release.toml` contract
- reusable CalVer and SemVer templates
- validation for the skill packages and templates
- installation documentation for this skill source

`iancleary/forge` continues to own:

- its existing `forge release` compatibility surface
- Forge-specific release automation, tests, and documentation

`iancleary/skills` continues to own general portable engineering skills. It no longer owns `cut-release` after the migration gate passes.

## Proposed Tree

```text
release-skills/
├── AGENTS.md
├── README.md
├── install.md
├── PLAN.md
├── scripts/
│   └── check.sh
├── tests/
│   └── test_release.py
└── skills/
    ├── create-release-process/
    │   ├── SKILL.md
    │   └── templates/release/
    │       ├── README.md
    │       ├── cargo-calver-day-serial.release.toml
    │       ├── cargo-semver-exact.release.toml
    │       ├── cargo-semver-gitea.release.toml
    │       ├── cargo-semver-github.release.toml
    │       └── scripts/
    │           ├── calver_day_serial.py
    │           └── release.py
    ├── cut-release/
    │   └── SKILL.md
    └── release-runner/
        └── SKILL.md
```

Do not add duplicate top-level copies of the templates. The copies under `create-release-process/templates/release/` are canonical.

## Work Plan

### 1. Bootstrap `release-skills`

- Add repo instructions in `AGENTS.md`.
- Add a short human overview and skill catalog in `README.md`.
- Add the repository installation contract in `install.md`.
- Copy `create-release-process` and `release-runner` from `iancleary/forge`.
- Copy `cut-release` from `iancleary/skills`.
- Copy the release templates only from Forge's `create-release-process` package.
- Add a standard-library Python runner that target repositories can copy and run
  with `uv`.
- Record the source commits used for the migration in the initial commit or pull request description.

Expected result: the new repository contains the complete release-skill capability without depending on files from either source checkout.

### 2. Normalize the skill contracts

- Keep `create-release-process` as the maintenance skill. It creates, audits, or repairs a deterministic repo-local release workflow.
- Keep `cut-release` as the general execution skill. It follows any existing checked-in release runner.
- Keep `release-runner` as the narrow adapter for repositories that use
  `release.toml` with the bundled Python runner.
- Remove Forge-repository policy and Forge CLI requirements from the portable
  skill bodies.
- Make routing explicit:
  - workflow creation or repair → `create-release-process`
  - ordinary release with a general repo-local runner → `cut-release`
  - `release.toml` plus `scripts/release.py` → `release-runner`
- Keep each `SKILL.md` frontmatter limited to `name` and `description`.

Expected result: the three names remain useful and non-overlapping. No rename or installed-directory migration is required.

### 3. Add validation

- Add `scripts/check.sh` as the repository's single local validation entrypoint.
- Run the Codex skill validator against all three skill directories.
- Check that each template parses as TOML.
- Check that the CalVer helper has valid Python syntax and supports `--help`.
- Run focused tests for config validation, safe path handling, command results,
  dry-run argument forwarding, SemVer bumps, and restoration of Cargo files.
- Assert the template invariants currently checked by Forge:
  - CalVer uses unprefixed tags by default.
  - the GitHub template selects GitHub
  - the Gitea template selects Gitea
  - the exact-version template requires release notes
- Run `git diff --check`.

Expected result: template and packaging regressions fail in the owning repository.

### 4. Establish the installation source

- Commit the initial repository contents.
- Configure the user's skill installation mechanism to install `iancleary/release-skills`.
- Install or link all three skills into the expected skill directory.
- Verify that each installed `SKILL.md` resolves to the new repository content.
- Verify automatic discovery in a fresh Codex session.

This is the migration gate. Do not remove the old copies until this step passes.

Expected result: removing the source copies from Forge and `skills` cannot remove the installed capability.

### 5. Remove release-skill ownership from Forge

In `iancleary/forge`:

- Remove `.agents/skills/create-release-process/`.
- Remove `.agents/skills/release-runner/`.
- Remove both entries from `config/release-skills.toml`.
- Remove both embedded skill declarations and their embedding tests from `crates/forge/src/main.rs`.
- Remove `examples/release/`; link to the canonical Python-backed templates in
  `iancleary/release-skills` instead.
- Reduce `scripts/check-release-process.sh` to checks owned by Forge's CLI and repo-local release workflow. Move template checks to `release-skills/scripts/check.sh`.
- Update `AGENTS.md`, `README.md`, `codex/user/AGENTS.md`, `docs/scope.md`, `docs/forge-skills.md`, `docs/forge.md`, `docs/release.md`, and `docs/codex.md` so they describe external skill ownership.
- Keep Forge-specific instructions that tell agents when to use the externally installed skills.
- Keep Forge's compatibility command and its own release automation unchanged
  unless removal exposes a genuine coupling. Do not make the external skills
  depend on that command.

Expected result: Forge does not package general release skills or template
copies, and the external skills do not require a Forge installation.

### 6. Remove `cut-release` ownership from `skills`

In `iancleary/skills`:

- Remove `skills/cut-release/`.
- Remove it from the catalog in `README.md`.
- Update `AGENTS.md`, `CLAUDE.md`, and `docs/release.md` to refer to the externally installed skill without claiming repository ownership.
- Document the installed-copy migration according to `docs/skill-retirement.md`.
- Check for stale active references.

Expected result: `iancleary/skills` no longer distributes `cut-release`, while its own release process can still route agents to the installed skill.

### 7. Verify each repository

Run in `release-skills`:

```sh
./scripts/check.sh
git diff --check
```

Run in `forge` using its documented task runner:

```sh
just check
git diff --check
```

Also run any narrower Forge release-process check retained by the repository.

Run in `skills`:

```sh
uv run <skill-creator>/scripts/quick_validate.py skills/<changed-skill>
git diff --check
```

For the removal-only change, validate every remaining active skill or use the repository's aggregate validator if one exists.

Finally:

- search all three repositories for stale ownership claims
- confirm all three installed skills come from `release-skills`
- inspect the complete diffs before commits
- make separate commits in each repository
- push only after explicit approval

## Commit Sequence

Use this order so every intermediate state remains recoverable:

1. `release-skills`: add the three skills, templates, docs, and validation.
2. installation configuration: add and verify the new source.
3. `forge`: remove embedded skills and template copies; update ownership docs.
4. `skills`: remove `cut-release`; update retirement and routing docs.

Do not combine changes from different repositories into one commit or overlap mutating Git commands.

## Acceptance Criteria

- `iancleary/release-skills` is the only source repository for the three release skills.
- The CalVer and three SemVer templates exist once in the new repository.
- The templates use the checked-in Python runner through `uv`, not Forge
  built-ins.
- All three skill names remain installed and discoverable.
- `create-release-process`, `cut-release`, and `release-runner` have distinct routing contracts.
- Forge no longer embeds or validates the external skill packages.
- Forge's compatibility command and its own release workflow still pass their
  checks.
- `iancleary/skills` no longer distributes `cut-release`.
- Each repository's documentation names the correct owner.
- No source repository is pushed until its diff is reviewed and approval is given.

## Deferred Work

- Do not create a compiled release CLI or published package in this repository.
- Do not copy the Forge implementation into this repository. Keep the Python
  runner small and workflow-bound.
- Do not rename the three skills during migration.
- Do not add more language, package-manager, or hosting-provider templates without a demonstrated repository need.
- Do not publish packages or cut releases as part of the migration.
