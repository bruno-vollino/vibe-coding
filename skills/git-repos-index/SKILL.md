---
name: git-repos-index
description: Create or update an index file of all git repos in the workspace
---

## Process
1. Traverse all workspace subfolders up to 3 levels deep and list every git repository found.
2. Save the results as a steering file. Ask the user where to save it (default: `workspace-repos.md` in the workspace root).
