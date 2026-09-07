# Release Process Templates

These templates are starting points for repositories that use the bundled
Python runner and its `release.toml` contract.

Copy the closest `*.release.toml` file to the target repo as `release.toml`,
copy `scripts/release.py`, then adjust the release name, provider, checks, tag
prefix, branch, notes policy, and version files. Run it with `uv`:

```sh
uv run scripts/release.py check --json
uv run scripts/release.py plan --json
uv run scripts/release.py run --dry-run --bump patch --json
```

Use `scripts/calver_day_serial.py` when a repo wants semver-compatible CalVer
versions like `YYYYMMDD.0.0`, `YYYYMMDD.0.1`, and the next date's
`YYYYMMDD.0.0`. The final numeric component starts at `0` each date.

Keep the Python scripts standard-library only when adapting them.

Use `semver-version-file-github.release.toml` when a repository has no package
manifest and stores its released version in a plain `VERSION` file. Replace the
example check command with the repository's complete local validation command.

Use `tag-only-github.release.toml` when a repository publishes a Git tag and
GitHub release without changing a manifest or version file. Pass the exact
consumer version with `--version`; it can be CalVer or another Git-tag-safe
scheme. Configure `current_version_command` and `next_version_command` when the
repository can derive those values deterministically.

## Execution Contract

Declare validation once in `[checks].commands` as argument arrays. The `run`
command enforces checks in both dry-run and apply. A failed check prevents
publication even when the caller skips `check`.

The bundled templates set `release.runner_protocol = "prepared-v1"`. The outer
command forwards `--contract <absolute-config-path>` to the runner. The bundled
runner loads that file and runs its checks after preparing version files and
before any commit or tag. A custom runner must implement that protocol before
selecting it. Without this setting, the outer command runs checks before
executing the configured command. Old `--check` arguments remain supported but
should be removed when their commands move into `[checks]`.

On a failed check, Cargo and version-file runners restore their original version
files before returning an error. They stop if checks change HEAD or files outside
the version targets. Once Git commit/tag/push begins, failures preserve the
partial state for inspection rather than attempting an automatic rollback.

`release.publish = false` disables apply, including direct bundled-runner calls
that supply `--contract`. Configuration and check commands are trusted repo code.

## Version Policy and Plans

Consumer versions are opaque. Cargo and version-file runners interpret SemVer;
tag-only releases accept any safe Git tag. Use `validate_version_command` to
enforce additional consumer policy. The runner appends the exact version as one
argument, without a shell. This validation runs during explicit-version planning
and execution; SemVer runners also validate their resolved version before edits.

```toml
validate_version_command = ["uv", "run", "scripts/release_policy.py", "validate"]
```

`plan --version <value>` or `plan --bump <level>` returns the selected version,
target commit, config SHA-256, and the bundled runner's intended tag. It performs
queries and version validation, but does not run checks or authenticate. Its
`ready` value is `null` and `checks_verified` is `false`. Successful planning has
exit status zero. `check` readiness covers only its configured checks. A
successful dry-run also covers the selected runner's preflight conditions.

Pass the plan's version, target_commit, and config_sha256 to execution:

```sh
uv run scripts/release.py run --dry-run --version VERSION --expected-head COMMIT --expected-config SHA256 --json
uv run scripts/release.py run --apply --version VERSION --expected-head COMMIT --expected-config SHA256 --json
```

These guards reject a stale commit or configuration. Built-in execution also
checks for HEAD changes during checks. Query-based version inference remains
explicit: run does not silently choose a new version when the date changes.

## Resume GitHub Publication

If tag push succeeded but GitHub publication failed, inspect the tag and its
commit. From a clean checkout of that commit, use:

```sh
uv run scripts/release.py run --dry-run --resume --version VERSION --expected-head TAG_COMMIT --json
uv run scripts/release.py run --apply --resume --version VERSION --expected-head TAG_COMMIT --json
```

Resume requires an existing remote tag at exactly TAG_COMMIT and rejects any
conflicting local tag. It reruns checks, does not bump files, commit, move tags,
or push, and only completes GitHub publication. An already published matching
release is a no-op. Drafts and API failures other than an explicit 404 stop the
operation. Resume supports all three bundled runners with GitHub; Gitea recovery
remains manual. An absent remote tag or a failure before tag push requires
manual inspection. For manifest releases, TAG_COMMIT is the generated release
commit, which differs from the original plan's input commit.

The GitHub API transport uses the documented
[gh api header output](https://cli.github.com/manual/gh_api) to distinguish a
missing release from authentication or network failures.

## Vendored Runner Provenance

Record the source when copying the unchanged runner into a consumer:

```toml
[runner_source]
repository = "https://github.com/iancleary/release-skills"
revision = "FULL_40_CHARACTER_GIT_COMMIT"
sha256 = "SHA256_OF_SCRIPTS_RELEASE_PY"
```

Every config load verifies the local runner checksum when this table exists.
This detects accidental drift; it is not a signature or an online upstream
verification. To update, inspect an explicit upstream commit, copy its bundled
runner, record its commit and checksum, then run consumer regression tests.
Keep consumer policy outside the vendored file.

## Migrating from v0.2.0

Plan's `ready` is now nullable. Consumers of JSON must use the exit status for
planning success and `checks_verified` for check status; do not interpret null
as a failed query. Command-runner contracts now enforce `[checks]` before run.
Bundled runners should adopt `prepared-v1` and remove duplicate `--check` flags
so validation runs once against the prepared tree. Existing direct runner flags
remain available for compatibility. Plan guards and source checksums are opt-in;
new consumer setups should use both.
