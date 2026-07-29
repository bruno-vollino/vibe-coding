---
name: git-pull
description: Execute git pull in one or multiple repositories
---

## Find git repositories
1. Look for a steering file listing all git repos in the workspace.
2. If none exists, execute the `git-repos-index` skill first.

## Update each repo

Process each repo individually (do NOT batch into a single script).

1. Check for uncommitted changes (`git status --porcelain`). If dirty, show the changed files and ask the user to choose:
   - **stash**: `git stash push -m "git-pull auto-stash"`
   - **cleanup**: `git clean -fd ; git reset HEAD --hard`
   - **resolve manually**: wait for user confirmation, then re-check from step 1
2. Switch to the default branch — try `main` first, fall back to `master`.
3. Run `git pull`. If it fails with a ref lock error, run `git gc --prune=now` and retry.
