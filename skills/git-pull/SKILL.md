---
name: git-pull
description: Helper to execute git pull in one or multiple repositories
---

## Find git repositories
1. Look for a steering file with all git repos in the workspace
2. If there is none, execute skill git-repos-index
3. Start updating each repo as instructed in the next section

## Update each git repo

Run each repo individually (do NOT batch into a single script).

1. Check if there are uncommitted changes (`git status --porcelain`). If there are any, present a list of files and summary of changes, pause and ask what to do:
    - 1.1 **stash**: `git stash push -m "git-pull auto-stash"`
    - 1.2 **cleanup**: `git clean -fd; git reset HEAD --hard`
    - 1.3 **resolve manually**: wait for user confirmation to continue, then return to step 1.
2. Switch to the default branch. Try `git checkout main` first; if it fails, try `git checkout master`.
3. Execute `git pull`
4. If git pull fails with a ref lock error, run `git gc --prune=now` then retry `git pull`.

## Shell compatibility
- Use `;` as command separator (works in both PowerShell and bash)
- Never use `&` or `&&` as command separator (PowerShell does not support it)
