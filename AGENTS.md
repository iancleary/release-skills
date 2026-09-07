# AGENTS.md

Guidance for contributors and coding agents working in `iancleary/release-skills`.

## Agent Entry Prompt

When a user supplies this repository URL to configure a consuming project's
releases, start with the [README prompt](README.md#prompt-for-your-agent):

> Use https://github.com/iancleary/release-skills to set up or execute this
> repo's release workflow. Preserve the repo's version policy—SemVer, CalVer,
> or another documented scheme. Use `create-release-process` for setup or
> maintenance, `release-runner` for the bundled Python `release.toml` workflow,
> and `cut-release` for another existing runner. Keep repository policy in
> TOML and small helpers, pin the unchanged shared runner by commit and
> checksum, and verify checks, planning, and dry-run before publishing.
> Publish only when explicitly requested. Install skills project-locally if
> needed; do not install globally.

"This repo" in the prompt means the consuming project, not `release-skills`.
Read its local instructions and the selected skill before acting:

- [create-release-process](skills/create-release-process/SKILL.md)
- [release-runner](skills/release-runner/SKILL.md)
- [cut-release](skills/cut-release/SKILL.md)

Keep both prompt copies aligned. A URL alone does not authorize publication.
The remaining instructions govern maintenance of `release-skills` itself.

## Purpose

This repository owns reusable release workflow skills, a portable Python
release runner, and the templates bundled with those skills. It does not own a
target repository's release policy.

Use this repository for:

- release workflow creation and maintenance guidance
- ordinary release execution guidance
- the portable `release.toml` runner and its adapter guidance
- reusable release templates

Keep the three skill contracts distinct:

- `create-release-process` creates, audits, or repairs a release workflow.
- `cut-release` executes an existing general repo-local release workflow.
- `release-runner` executes `release.toml` through the bundled Python runner.

## Before Editing

- Check `git status --short --branch`.
- Read `PLAN.md` and the skill or template you plan to change.
- Keep unrelated executable tooling out of this repository.
- Keep target-repository policy in that target repository.
- Preserve the installed skill names during migrations.

## Skill Rules

- Each skill lives under `skills/<skill-name>/`.
- Each `SKILL.md` frontmatter contains only `name` and `description`.
- The frontmatter name matches the directory name.
- Descriptions define narrow and distinct trigger contracts.
- Keep instructions portable unless a skill explicitly adapts a named tool.
- Keep release templates only under
  `skills/create-release-process/templates/release/`.

## Validation

Run the repository check after changing a skill, template, or validation rule:

```sh
./scripts/check.sh
```

The check validates skill packages, TOML templates, the CalVer helper, template
invariants, and Git whitespace.

## Releases

Read `docs/release.md` before release work.

- Use `create-release-process` to maintain this workflow.
- Use `release-runner` for an ordinary release.
- Use `uv run scripts/release.py check --json` and
  `uv run scripts/release.py plan --json` for read-only inspection.
- Use `uv run scripts/release.py run --dry-run --bump <level> --json` to verify
  release intent.
- Run `--apply` only when the user explicitly asks to publish a release.
- Keep `VERSION`, `release.toml`, `docs/release.md`, and both checked-in runner
  copies aligned. `scripts/check.sh` rejects runner drift.

## Safety

- Do not publish, push, tag, or upload a release while maintaining these skills.
- Inspect and validate changes before installation or migration work.
- Do not remove an old skill source until the replacement installation is
  verified in a fresh Codex session.
- Never commit credentials, tokens, or private repository details.

## Writing Style

Write short, direct instructions for future agents. Prefer command contracts,
decision rules, safety boundaries, and observable verification.
