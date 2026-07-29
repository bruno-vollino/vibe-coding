---
name: jira-gitlab-merge-request
description: Create a merge request in gitlab
---

## Process
1. Determine the repo's default branch (`main` or `master`) via the GitLab MCP server.
2. Create a merge request from the current subtask branch to the default branch (GitLab MCP server):
   - Title: `${issueKey} [${subTaskKey}] ${issueSummary} [${subTaskSummary}]` (same as the commit message from jira-commit-push)
   - Assignee: the user matching the git commit author name
