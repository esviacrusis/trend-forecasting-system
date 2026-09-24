# Trend Forecasting System Cleanup Recovery Runbook

This runbook resumes the project cleanup safely and step by step.

Guiding rule: **audit first, approve second, modify third, validate last**.

## Progress tracker

- [x] Phase 1: Read-only audit completed on 2026-09-23.
- [x] Phase 2: File dispositions reviewed and approved on 2026-09-23.
- [x] Phase 3: Clean recovery branch created as cleanup/project-structure-resumed.
- [x] Phase 4: Approved source, database, and documentation assets imported.
- [x] Phase 6: Ignore rules and placeholder environment template added.
- [ ] Phase 5: Final structural organization and code review.
- [x] Phase 8: Safe validation completed on 2026-09-23; database/network tests pending.
- [ ] Phase 9: Final review and commits.

Current working copy:

~~~text
/private/tmp/trend-forecasting-system-recovery
~~~

Validation completed:

- requirements installed successfully in an isolated Python 3.9 environment;
- pip dependency check passed;
- all 14 declared third-party modules imported successfully;
- Python compilation passed with a redirected cache location;
- configuration module imported successfully;
- database, scraping, API, and production-data operations were not run.

## 0. Important paths and branches

Repository/workspace root:

~~~text
/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes
~~~

Project folder:

~~~text
/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/trend-forecasting-system
~~~

Known recovery branch: recovery-cleanup

Unfinished branch: cleanup/project-structure

Backup bundle:

~~~text
/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes/trend-forecasting-system-before-history-cleanup.bundle
~~~

Do not delete the backup bundle until cleanup is complete and verified.

## 1. Run the read-only audit

Use the complete audit prompt prepared for this project. The audit must not:

- modify files, branches, refs, remotes, or configuration;
- switch branches or create worktrees;
- stage, commit, reset, rebase, or rewrite history;
- create temporary files or reports;
- print passwords, tokens, API keys, or connection strings.

The audit should report:

- current repository and branch status;
- what is included in recovery-cleanup;
- backup bundle integrity and advertised refs;
- tracked, untracked, ignored, generated, temporary, sensitive, duplicate, and important files;
- differences between the current project and recovery-cleanup;
- structural problems and redacted security findings;
- proposed cleanup actions requiring approval.

### Checkpoint 1

Save the audit report. Do not make changes until every important file has a proposed disposition:

- keep and track;
- keep locally and ignore;
- archive;
- remove with approval;
- investigate further.

## 2. Review and approve file decisions

Use this follow-up prompt:

~~~text
Review the audit report above. Do not modify anything yet.

Create a file disposition table with these columns:
- path
- category
- proposed action
- reason
- risk
- approval required

Group the table into keep, ignore, archive, remove, and investigate. Highlight anything ambiguous or potentially newer than recovery-cleanup.
~~~

### Checkpoint 2

Confirm the disposition table. Only then proceed to cleanup.

## 3. Establish the cleanup working branch

Because cleanup/project-structure currently has no commits, use recovery-cleanup as the baseline. Leave the original folder untouched until the baseline is established.

The safest approach is to use a separate worktree outside the project folder:

~~~bash
cd "/Users/eric/Documents/CSUEB Subjects/2026 Spring/BAN 693 Capstone/Codes"
git worktree add /private/tmp/trend-forecasting-system-recovery recovery-cleanup
cd /private/tmp/trend-forecasting-system-recovery
git switch -c cleanup/project-structure-resumed
git status
~~~

Expected result: the new branch is based on recovery-cleanup and has a clean working tree.

Do not continue if Git reports conflicts or unexpected files. Stop and review the message first.

### Checkpoint 3

Confirm:

~~~bash
git branch --show-current
git log --oneline -5
git status --short
~~~

The current branch should be cleanup/project-structure-resumed, and the status should be clean.

## 4. Reconcile current files with the baseline

Compare the original project folder with the new clean worktree. Bring over only files approved in the disposition table.

Use this prompt before copying anything:

~~~text
Compare the original project folder with the cleanup-project-structure-resumed worktree.

Use only the approved file disposition table. Do not delete or overwrite anything.

List the exact files that should be copied, their destination, and whether each copy is new or replaces an older version.
Wait for approval before performing the copies.
~~~

### Checkpoint 4

Review the exact copy list and approve only the listed files.

## 5. Apply structural cleanup

After approval, organize the project into clear areas for source code, tests, documentation, data, and generated output. Preserve behavior while moving files.

Recommended outcomes:

- active application code is separated from backups and experiments;
- generated files are outside tracked source areas or ignored;
- local data is clearly identified and ignored when appropriate;
- documentation is easy to find;
- duplicate or obsolete files are archived or removed only with approval.

Use a separate prompt for each logical change:

~~~text
Perform only the approved structural changes listed below:
[paste the approved actions]

Before changing anything, show the exact files affected and the resulting paths.
Do not delete files, modify unrelated files, or change Git history.
~~~

## 6. Apply security and configuration cleanup

Confirm that:

- no real credentials are tracked;
- .env remains local and ignored;
- configuration uses environment variables;
- .env.example contains placeholders only;
- remote URLs and reports do not expose credentials.

Use this redacted security review:

~~~text
Perform a read-only security review of the current cleanup branch.

Report only filenames, line numbers, and redacted descriptions. Never print secret values.
Check tracked files, ignored files, configuration loading, connection strings, API keys, passwords, and tokens.
Do not modify anything.
~~~

## 7. Update documentation and ignore rules

The final project should explain:

- what the system does;
- how to install dependencies;
- which environment variables are required;
- how to run the application;
- how to run tests or smoke checks;
- which data and outputs are local or generated.

The .gitignore should cover local secrets, operating-system files, temporary Office files, generated outputs, local datasets, and backup scripts as appropriate.

## 8. Validate the project

Run only checks appropriate for the project and available dependencies:

~~~bash
python -m compileall .
git diff --check
git status --short
~~~

Then run the documented tests or smoke checks. Do not run production data ingestion or destructive database operations without explicit approval.

Record failures instead of hiding them.

### Checkpoint 5

Review:

- test results;
- security results;
- git diff;
- changed file list;
- remaining warnings or limitations.

## 9. Commit the cleanup

Only after the final review, create small logical commits. Suggested commit groups:

~~~text
chore: establish project structure
chore: update ignored files and local configuration safeguards
refactor: consolidate configuration
docs: document setup and project usage
~~~

Before committing:

~~~bash
git status
git diff --stat
git diff --check
~~~

## 10. Confirm the finish line

Cleanup is complete when all of the following are true:

- the cleanup branch is based on recovery-cleanup;
- the working tree is clean;
- only intentional files are tracked;
- no secrets are tracked or exposed;
- generated, temporary, and local files are ignored or archived;
- the project structure is understandable;
- setup and usage are documented;
- validation checks pass or documented limitations are accepted;
- the backup bundle remains available;
- final commits have clear messages;
- unresolved issues are listed explicitly.

The end state is not “everything was deleted.” The end state is a safe, organized, reproducible project that can be restored and understood later.
