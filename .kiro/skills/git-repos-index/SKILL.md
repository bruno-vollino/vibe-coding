---
name: git-repos-index
description: Create or update the single workspace index of all git repositories
---

## The index has exactly one location

`<workspace-root>/.kiro/steering/git-repositories.md`

Never create a second copy of this list. In particular:

- Do **not** write it into a skill directory (no `repos.txt` next to a skill).
- Do **not** create an alternative filename such as `workspace-repos.md`.
- Do **not** commit it to the personal config repo (`vibe-coding`); the paths are machine-specific
  and belong to the workspace, not to the config.

If you find more than one repo list, merge them into the file above, verify the merged list against
disk, and delete the others.

## Format

The filename must match the steering `name`, so both are `git-repositories`:

```markdown
---
inclusion: auto
name: git-repositories
description: Index of every git repository in the workspace, with absolute paths. Single source of truth for repo locations.
---

# Workspace Git Repositories

## Root: `c:\workspace\git`

### <domain>
- `c:\workspace\git\<domain>\<repo>` — short description of what the repo is
```

Rules:

- One repo per bullet, absolute path in backticks first, then ` — ` and a short description.
- Group by domain with `###` headings, one `## Root:` section per workspace folder.
- Absolute paths only. The `git-pull` skill reads this file directly, and it keys off backticked
  absolute paths, so prose and headings are ignored automatically.

## Process

1. Enumerate repositories from disk. Reuse the bundled scanner from the `git-pull` skill rather than
   walking the tree by hand:

   ```
   python3 ../git-pull/scripts/git_pull.py --scan <workspace-root> --depth 3
   ```

   Pass `--scan` once per workspace folder. It stops descending at each `.git`, so it is cheap.
2. If the index already exists, treat it as the source of descriptions. Diff the scan against the
   paths in the file and only add what is missing or remove what is gone. **Never overwrite the file
   wholesale**: the descriptions are hand-written and a regeneration would destroy them.
3. For a repo you are adding, derive the description from evidence rather than guessing: the Maven
   `name`/`artifactId`, the module list, or the README. If you cannot tell what it is, say so instead
   of inventing a description.
4. Report what changed: repos added, repos removed, and any left without a description.