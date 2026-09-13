---
name: cut-release
description: "Execute an existing repository release runner. Use release-runner for the bundled Python release.toml contract, and create-release-process for workflow maintenance."
---

# Cut Release

Use this skill when the user wants to cut, publish, or ship the next normal release and the repo already has a deterministic release workflow.

Follow the target repo's local release contract.

## Use This When

- the release workflow already exists in the repo
- the user asks to cut, publish, ship, or create the next release
- a checked-in runner or task recipe owns the release sequence
- you should execute that runner instead of hand-building separate bump, tag, push, and publish commands

## Do Not Use This When

- the user wants to create, redesign, audit, or repair the release workflow itself
- the repo has no deterministic release runner yet
- the release script or docs are broken and need maintenance
- you are correcting an already-published release and need explicit manual repair steps

For workflow maintenance, use `create-release-process` if available. If the repo
uses the bundled Python `release.toml` runner, use `release-runner` when
available for that command contract.

## Local Contract First

Before running anything mutating:

- follow applicable repo instructions and read the documentation that owns the release contract
- inspect the task runner and release script named by those instructions
- identify the versioning scheme, such as SemVer, CalVer, or repo-specific date tags
- identify whether the repo accepts a release intent such as `--bump patch|minor|major`, can infer the next version, or requires `--version`
- identify how release notes are supplied, such as `--notes-file`, generated notes, or a template
- identify whether checked-in GitHub Actions, Gitea Actions, GitLab CI, or equivalent workflow files define the release gate
- identify the local checkout checks the runner expects when no checked-in workflow owns validation
- inspect git status and confirm the intended branch

The local repo contract overrides generic expectations in this skill.

## Execution Pattern

Prefer the repo's documented entrypoint:

- `uv run scripts/release.py run --apply --json`
- `uv run scripts/release.py run --dry-run --json`
- `just cut-release`
- `make release`
- package-manager release scripts

Use dry-run first when the repo supports it and either the user asked for verification or version inference, notes generation, file mutation, or publishing behavior has meaningful risk.

Use read-only version query commands when available instead of parsing manifests by hand.

When the runner supports release intent, pass the user's intended bump rather than
calculating the next version yourself. Supply an exact version when the user or
repo contract requires one.

Prefer the repo's local checkout checks when the release contract does not point to checked-in GitHub Actions, Gitea Actions, GitLab CI, or another committed release workflow. When committed workflows exist and are part of the release contract, use the runner's workflow-dispatch/watch path or follow the repo's documented handoff instead of substituting an ad hoc local-only check.

Do not reconstruct the flow with separate version bump, check, push, tag, and publish commands unless the user is explicitly repairing a release outside the normal path.

## GitHub Auth Boundary

Run every `gh auth ...` command outside the sandbox. The sandbox can hide or misreport keyring-backed GitHub credentials, so a sandboxed auth failure is not authoritative.

- `gh auth status`
- `gh auth login`
- `gh auth refresh`

For release work, check GitHub CLI auth with an outside-sandbox `gh auth status` before treating auth as missing or broken. Run other release commands outside the sandbox only when they need Git metadata writes, network access, public mutation, or keyring-backed credentials in the current environment.

Repo-local release runners are allowed to vary. Before executing a runner,
inspect the entrypoint and directly delegated helper scripts for `gh auth`. If
the runner calls `gh auth`, may call it through an uninspected helper, or is too
opaque to verify, run the whole runner outside the sandbox to avoid a hidden
sandboxed auth failure.

## Output

Report:

- whether you ran dry-run, real release, or both
- the version that was printed or cut
- how release notes were supplied
- whether the repo runner succeeded
- the workflow run and release URLs, or the failing step if publication did not complete

## Safety

Release runners may commit, push, tag, upload artifacts, publish packages, deploy, or create public releases.

If the repo is not in a safe release state, pause publication and diagnose the
blocker. Continue repairs within the authorized scope and rerun failed gates.
Ask before unrelated workflow changes or manual recovery outside the contract.
Do not bypass a failed gate to force publication.
