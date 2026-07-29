---
name: jira-gitlab-merge-request
description: Create a merge request in gitlab
---

## Process
1. Use the gitlab mcp server to check what is the default main branch for the reop: "main" or "master".
2. Create a merge request in Gitlab, from the Jira subtask branch to the main branch. use the gitlab mcp server.
    1.1 The title should be the same as first commit message, from jira-commit-push: ${issueKey} [${subTaskKey}] ${issueSummary} [${subTaskSummary}]
    2.2 Assign to the user corresponding to the git commit author name