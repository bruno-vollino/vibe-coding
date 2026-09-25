---
name: jira-commit-push
description: Commit all changes and push to a branch in gitlab
---

## Process
1. Fetch the story and subtask by key from Jira (use Atlassian MCP server). If no subtask key was provided, ask for it.
2. Switch to a branch named by the subtask key (e.g. `TRA-111111`), if not already on it.
3. Commit with message: `${issueKey} [${subTaskKey}] ${issueSummary} [${subTaskSummary}]`
4. Push the branch to origin.
