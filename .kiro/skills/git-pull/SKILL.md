---
name: git-pull
description: Execute git pull in one or multiple repositories
---

## Find git repositories
1. Look for a steering file listing all git repos in the workspace.
2. If none exists, execute the `git-repos-index` skill first.
3. Cross-check the steering list against the repos actually on disk (a `.git` directory at the expected path). Include any extra repos found, and skip any listed repo that is missing.

## Update repos

### On Windows: batch script first

On Windows, running each repo as a separate shell command is slow and the terminal echo is noisy. Prefer the bundled loop script, which still processes each repo individually (status check, default-branch detection, checkout, pull) and prints `===REPO===` / `===DONE===` markers so progress is visible.

Script: `scripts/git-pull.ps1`

It accepts the repo directories generically — pass them explicitly, from a file, or via the pipeline — and supports excludes:

```powershell
# Explicit list, excluding a domain (e.g. abelson)
.\scripts\git-pull.ps1 -Repo 'c:\ws\repo-a','c:\ws\repo-b' -Exclude 'abelson'

# From a file (one path per line; '#' comments and blank lines ignored)
.\scripts\git-pull.ps1 -RepoFile .\repos.txt -Exclude 'abelson'

# Piped
Get-Content repos.txt | .\scripts\git-pull.ps1
```

Behaviour: skips excluded and missing paths, skips dirty repos (never stashes or cleans automatically), detects `main` then `master`, checks out the default branch, pulls, and retries once after `git gc --prune=now` on a ref lock error.

Run it as a background process and poll its output so progress is visible in the shell.

If the script fails (cannot run, errors out early, or produces unusable output), fall back to processing each repo individually as described below.

### Fallback / non-Windows: process each repo individually

1. Check for uncommitted changes (`git status --porcelain`). If dirty, show the changed files and ask the user to choose:
   - **stash**: `git stash push -m "git-pull auto-stash"`
   - **cleanup**: `git clean -fd ; git reset HEAD --hard`
   - **resolve manually**: wait for user confirmation, then re-check from step 1
2. Switch to the default branch — try `main` first, fall back to `master`.
3. Run `git pull`. If it fails with a ref lock error, run `git gc --prune=now` and retry.

## Report

Summarize the run: how many repos pulled successfully, and list any that were skipped (dirty/excluded/missing) or failed. For dirty repos, do not stash or clean without explicit user confirmation.
