---
name: jira-commit-push
description: Commit all changes and push to a branch in gitlab
---

## Process
1. Fetch the story and subtask by key from Jira. If I have not provided it so far, as for the subtask key. Use the Jira/atlassian mcp server.
2. Switch to a branch named by the subtask key like "TRA-111111", if it is not already in it
2. Build a commit message in this format: ${issueKey} [${subTaskKey}] ${issueSummary} [${subTaskSummary}]
3. Push changes to the subtask  branch.