# AGENTS.md

Guidance for contributors and coding agents working in `iancleary/release-skills`.

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

## Safety

- Do not publish, push, tag, or upload a release while maintaining these skills.
- Inspect and validate changes before installation or migration work.
- Do not remove an old skill source until the replacement installation is
  verified in a fresh Codex session.
- Never commit credentials, tokens, or private repository details.

## Writing Style

Write short, direct instructions for future agents. Prefer command contracts,
decision rules, safety boundaries, and observable verification.
