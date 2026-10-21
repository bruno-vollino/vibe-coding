---
name: git-pull
description: Execute git pull in one or multiple repositories
---

## Find git repositories

The repo list lives in exactly one place: `<workspace-root>/.kiro/steering/git-repositories.md`.

Pass that file straight to `--repo-file`. The script reads backticked absolute paths out of the
markdown, so no plain-text copy is needed.

**Never create a second repo list.** Do not write a `repos.txt` next to this skill, and do not add
one to the `vibe-coding` config repo: the paths are machine-specific and belong to the workspace.
If the index is missing or stale, fix it in place with the `git-repos-index` skill.

## Update repos

Use the bundled script. It processes each repo individually (status check, default-branch detection,
checkout, pull) and prints `===REPO===` / `===DONE===` markers so progress is visible. Running one
shell command per repo is slow and noisy by comparison.

Script: `scripts/git_pull.py` (Python 3, standard library only, runs on Windows, macOS and Linux).

```
# Everything in the workspace index, excluding a domain
python3 scripts/git_pull.py --repo-file <workspace-root>/.kiro/steering/git-repositories.md --exclude abelson

# Explicit paths
python3 scripts/git_pull.py --repo /ws/repo-a --repo /ws/repo-b

# Piped
cat paths.txt | python3 scripts/git_pull.py
```

On Windows use `python` if `python3` is not on PATH.

Run it as a background process and poll its output so progress stays visible.

Behaviour per repo: skips excluded and missing paths, skips dirty repos (never stashes or cleans
automatically), detects `main` then `master`, checks out the default branch, pulls, and retries once
after `git gc --prune=now` on a ref lock error. Exits non-zero if any repo failed.

A `missing` count above zero means the index lists a repo that is no longer on disk. Report it so the
index can be corrected; do not silently ignore it.

## Fallback: process each repo individually

If the script cannot run, fall back to doing this per repo:

1. Check for uncommitted changes (`git status --porcelain`). If dirty, show the changed files and ask
   the user to choose:
   - **stash**: `git stash push -m "git-pull auto-stash"`
   - **cleanup**: `git clean -fd` then `git reset HEAD --hard`
   - **resolve manually**: wait for user confirmation, then re-check from step 1
2. Switch to the default branch, trying `main` first and falling back to `master`.
3. Run `git pull`. If it fails with a ref lock error, run `git gc --prune=now` and retry.

## Report

Summarize the run: how many repos pulled successfully, and list any that were skipped
(dirty/excluded/missing) or failed. For dirty repos, never stash or clean without explicit user
confirmation.