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
