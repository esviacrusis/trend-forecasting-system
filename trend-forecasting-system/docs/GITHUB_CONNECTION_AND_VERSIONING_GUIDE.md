# GitHub Connection and Versioning Guide

## Current state

This project is a Git repository, but its current `origin` points to a temporary local recovery path, not GitHub. The current branch is `cleanup/project-structure-resumed`; it is two commits ahead of that temporary reference, and there are uncommitted document changes.

Do not force-push, delete branches, or discard changes while reconnecting.

## Safe connection workflow

1. Confirm the exact GitHub URL with the project owner:

   `https://github.com/ORGANIZATION/REPOSITORY.git`

2. Inspect the current state:

   `git status --short --branch`

   `git branch -vv`

   `git remote -v`

3. Keep `.env` and `.env.*` local. Never commit real passwords, API keys, AWS keys, database URLs, or tokens. If a credential was ever committed, rotate it.

4. Add GitHub as a separate remote so the current configuration is preserved:

   `git remote add github https://github.com/ORGANIZATION/REPOSITORY.git`

   `git remote -v`

   `git fetch github --prune`

   `git branch -r`

5. Compare histories, assuming the central branch is `main`:

   `git log --oneline --graph --decorate HEAD github/main`

   `git diff --stat github/main...HEAD`

   `git log --oneline github/main..HEAD`

   `git log --oneline HEAD..github/main`

   Stop if the histories diverge unexpectedly.

6. Review local changes before committing:

   `git status`

   `git diff -- docs`

7. After reviewing intentional changes, commit only reviewed files:

   `git add docs/`

   `git diff --cached --check`

   `git commit -m 'docs: update database schema reference'`

8. Push a separate branch and open a pull request:

   `git push -u github cleanup/project-structure-resumed`

Do not push directly to `main`, use `--force`, or overwrite an existing shared branch.

## Team versioning model

Each member has an independent clone, remote configuration, and local branches. Changing your remote affects only your clone. Other members see your work after you push a branch.

Recommended workflow: central `main` or `develop` -> personal feature branch -> pull request -> review -> merge.

Before starting work:

`git fetch github --prune`

`git status`

For a conservative local `main` update:

`git switch main`

`git pull --ff-only github main`

If that fails, stop and review the divergence. Never use `git reset --hard` or `git clean -fd` without explicit approval.

## Versioning rules

- Make small, focused commits.
- Use descriptive commit messages.
- Fetch before beginning new work.
- Push branches regularly for backup.
- Use pull requests for review.
- Keep credentials and machine-specific files outside Git.
- Never rewrite shared history without explicit approval.

No GitHub remote, file, branch, or database changes should be made without the project owner's approval.
