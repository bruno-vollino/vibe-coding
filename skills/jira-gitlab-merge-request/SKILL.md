---
name: jira-gitlab-merge-request
description: Create a merge request in gitlab
---

## Process
1. Determine the repo's default branch:
   - Run `git ls-remote --symref origin HEAD` to check what the remote HEAD points to.
   - If that fails or is ambiguous, check if `origin/main` exists (`git rev-parse --verify origin/main`). If it exists, use `main`.
   - Only fall back to `master` if `origin/main` does not exist.
   - **Never assume `master` without checking `main` first.**
2. Create a merge request from the current subtask branch to the default branch (GitLab MCP server):
   - Title: `${issueKey} [${subTaskKey}] ${issueSummary} [${subTaskSummary}]` (same as the commit message from jira-commit-push)
   - Assignee: the user matching the git commit author name
