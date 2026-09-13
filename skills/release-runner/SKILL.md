---
name: release-runner
description: "Check, plan, or execute releases using the bundled Python release.toml and scripts/release.py contract. Use cut-release for other existing runners."
---

# Release Runner

Use this skill when a repository has `release.toml` and `scripts/release.py`, and
the user asks to check, plan, dry-run, cut, publish, or run a normal release.

For another repo-local runner, use `cut-release` instead.

The checked-in `release.toml` and `scripts/release.py` files are the contract.
The TOML file names the runner and read-only checks. Commands are string arrays;
the Python runner executes them directly without a shell.

For prepared-v1 contracts, run enforces the TOML checks against prepared version
files. Do not duplicate checks in runner arguments. Plan is descriptive: its
ready value is null until execution verifies prerequisites. Use the plan's
exact version, target_commit, and config_sha256 with --version, --expected-head,
and --expected-config for dry-run and apply. Stop on changed inputs and replan.

For a GitHub release that failed after tag push, explicitly use --resume with
the exact --version and --expected-head of the release tag. Inspect the tagged
commit first. Resume verifies the remote tag, reruns checks, and only completes
publication. Do not use --bump during recovery. Missing or conflicting tags
require manual inspection. See the installed create-release-process template
README for the full protocol when available.

For ordinary SemVer releases, pass the intended bump to the runner:

```sh
uv run scripts/release.py run --dry-run --bump patch --json
uv run scripts/release.py run --apply --bump minor --json
```

Use `--version <v>` only when the user or repository contract requires an exact
version, prerelease, build metadata, CalVer, date tag, or another specific
version. Consumer versions are otherwise opaque; only SemVer-specific runners
interpret their structure. Do not pass both `--bump` and `--version`.

For example, a tag-only CalVer repository can use:

```sh
uv run scripts/release.py run --dry-run --version 2026.09.07.0 --json
```

## Required Sequence

1. Read `release.toml` and `scripts/release.py`.
2. Run:

```sh
uv run scripts/release.py check --json
```

3. If `ready: false`, pause release execution and diagnose the failed check.
   Continue only after the gate passes. Otherwise run:

```sh
uv run scripts/release.py plan --json
```

4. For validation without publishing, run:

```sh
uv run scripts/release.py run --dry-run --bump patch --json
```

Replace `--bump patch` with the release intent required by the repository.

5. Only when the user explicitly asks to publish or apply the release, run:

```sh
uv run scripts/release.py run --apply --bump patch --json
```

Use the same verified release intent for apply.

## Safety

- Treat `check` and `plan` as read-only only after inspecting the configured
  commands. The checked-in configuration is trusted policy.
- Treat `run --dry-run` as a runner-controlled dry-run. It can contact remotes.
- Treat `run --apply` as mutating and public. It can commit, push, tag, publish,
  create releases, upload artifacts, or dispatch workflows.
- Run the release outside a restricted sandbox when the configured runner needs
  Git metadata writes, network access, or keyring-backed credentials.
- Do not substitute manual publish, tag, version bump, or release commands
  unless the checked-in runner is broken and the user explicitly asks for
  repair.
- A failed check, JSON error, or runner failure blocks dependent publication.
  Continue safe diagnosis and repairs already within the requested scope.
  Rerun the failed gate after repair; never bypass it. Ask before unrelated
  changes to release machinery or manual recovery outside the runner contract.

## Output

Report:

- release name
- current and next version when present
- check summary
- runner command
- whether dry-run or apply was executed
- the structured error when a command fails
