I want you to install Ian Cleary's release workflow skills. Execute the safe
installation and verification steps autonomously.

OBJECTIVE: Install the skills from `iancleary/release-skills` in the requested
scope so the agent can create, maintain, and execute deterministic release
workflows.

DONE WHEN: the selected scope lists `create-release-process`, `cut-release`, and
`release-runner`, and each installed `SKILL.md` resolves to this repository's
content.

## Step 0: Inspect Existing Installations

Determine whether the requested scope is repository-local, user-global, or
managed by a machine policy tool. Inspect the current skill listing before
changing it. If Forge or another policy manager owns skill installation, use
that policy-managed target.

Do not remove old source copies during this step. The migration gate passes only
after the replacement installation is verified.

## Step 1: Install

For a repository-local installation, run:

```sh
npx skills add iancleary/release-skills
```

For a user-global installation, run:

```sh
npx skills add iancleary/release-skills -g
```

## Step 2: Verify

For a repository-local installation, run:

```sh
npx skills list
```

For a user-global installation, run:

```sh
npx skills list -g
```

Confirm that the selected scope lists:

- `create-release-process`
- `cut-release`
- `release-runner`

Inspect the installed files or links. Confirm that each installed `SKILL.md`
matches the corresponding file from `iancleary/release-skills`. Start a fresh
Codex session and confirm that all three skills are discoverable.

Stop and report the failing step if installation, file resolution, or fresh
session discovery cannot be verified. Do not delete stale installed copies or
modify the old source repositories until all checks pass.
