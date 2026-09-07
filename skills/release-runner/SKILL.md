---
name: release-runner
description: "Use a repo-local Python runner and release.toml to check, plan, dry-run, or apply deterministic release workflows without reconstructing release steps by hand."
---

# Release Runner

Use this skill when a repository has `release.toml` and `scripts/release.py`, and
the user asks to check, plan, dry-run, cut, publish, or run a normal release.

For another repo-local runner, use `cut-release` instead.

The checked-in `release.toml` and `scripts/release.py` files are the contract.
The TOML file names the runner and read-only checks. Commands are string arrays;
the Python runner executes them directly without a shell.

For ordinary SemVer releases, pass the intended bump to the runner:

```sh
uv run scripts/release.py run --dry-run --bump patch --json
uv run scripts/release.py run --apply --bump minor --json
```

Use `--version <v>` only when the user or repository contract requires an exact
version, prerelease, build metadata, CalVer, date tag, or another specific
version. Do not pass both `--bump` and `--version`.

## Required Sequence

1. Read `release.toml` and `scripts/release.py`.
2. Run:

```sh
uv run scripts/release.py check --json
```

3. Stop if the result reports `ready: false`. Otherwise run:

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
- Stop on a failed check, a JSON error, or a runner failure.

## Output

Report:

- release name
- current and next version when present
- check summary
- runner command
- whether dry-run or apply was executed
- the structured error when a command fails
