---
name: gitlab-diff-comments
description: Post code review comments anchored to specific lines in a GitLab merge request diff
---

## When to use

Any time review comments must land on lines in the MR diff rather than as general notes at the
bottom of the merge request.

## Prerequisites

- `glab` on PATH and authenticated (`glab auth status`). Set `GITLAB_HOST` for self-managed
  instances, e.g. `git.entaingroup.com`.
- `python3` (or `python` on Windows) for the bundled script. Standard library only.
- Ideally a local checkout of the MR source branch, so anchors can be validated before posting.

## Why not the GitLab MCP server

The MCP `create_merge_request_note` tool has **no** `position` parameter, so it can only create
general notes. It cannot anchor a comment to a line. Do not attempt it; use the script below.

## Process

1. Get the diff. If the repo is checked out locally on the MR source branch, use the local range:

   ```
   git -C <repo> fetch origin
   git -C <repo> diff origin/<target_branch>...HEAD
   ```

   Confirm the range is right by checking that `git merge-base origin/<target> HEAD` equals the
   MR's `diff_refs.base_sha`. If there is no local checkout, save the MR diff to a file and pass
   `--diff-file` instead.

2. List the lines available as anchors. Only **added** (`+`) lines are safe: an unchanged line is
   either rejected or lands somewhere unintended.

   ```
   python3 scripts/gitlab_diff_comments.py anchors \
       --git-range origin/master...HEAD --repo <repo> --filter <path or text>
   ```

   Output is `path<TAB>line<TAB>text`.

3. Write the comments to `.review/comments.json` in the repo. Agent permission rules allow writes
   under `.review/` without prompting, and the directory is throwaway, so keep review artifacts there:

   ```json
   [
     {"file": "src/main/java/com/example/Foo.java", "line": 84, "body": "Markdown body."},
     {"file": "src/api/foo.ts", "line": 21, "body": "Another comment."}
   ]
   ```

   Write this with a file-writing tool, not by building a shell string: comment bodies contain
   backticks and quotes that shells mangle.

4. Dry run first. With `--git-range` (or `--diff-file`) the script validates every anchor against
   the diff and refuses to post if any is not an added line:

   ```
   python3 scripts/gitlab_diff_comments.py post \
       --project <group/sub/repo or numeric id> --mr <iid> \
       --comments .review/comments.json --git-range origin/master...HEAD --repo <repo> --dry-run
   ```

5. Post. Drop `--dry-run`, keep the validation flags:

   ```
   python3 scripts/gitlab_diff_comments.py post \
       --project <group/sub/repo> --mr <iid> \
       --comments .review/comments.json --git-range origin/master...HEAD --repo <repo>
   ```

   Each line prints `OK` or `FAIL`. The script checks every created note came back as a
   `DiffNote` on the expected line, and exits non-zero if any comment failed.

6. Report the final `file:line` anchors back to the user.

## API details worth knowing

- Endpoint: `POST /projects/:id/merge_requests/:iid/discussions`.
- The `Content-Type: application/json` header is **required**. Without it the API returns
  `The provided content-type '' is not supported`.
- `position` needs `base_sha`, `start_sha`, `head_sha` (all from the MR's `diff_refs`),
  `position_type: "text"`, `new_path`, `old_path` and `new_line`.
- For a newly added file, set `old_path` equal to `new_path` and omit `old_line`.
- A project path must be URL-encoded in the API path (`group%2Fsub%2Frepo`). The script does this.
- A successful response contains `notes[0].type == "DiffNote"` with the position echoed back. A
  general note comes back as `Note`, which means the position was ignored.

## Ad-hoc GitLab reads: spell out --method GET

When reading from the API outside this script, write `glab api --method GET <path>`. Agent
permission rules allow that form but never a bare `glab api`, so an allow-listed pattern cannot
express a write. Anything that writes to GitLab prompts by design.

## Troubleshooting

- `FAIL ... 400 Bad Request` on a line that looks correct: the anchor is probably not part of the
  diff, or the MR has been pushed to since you read `diff_refs`. Re-read the MR and recompute.
- Comments land in the wrong place: you anchored to a context line. Use the `anchors` subcommand.
- Nothing posts and `glab` reports a 404: check `GITLAB_HOST`, and that the project path or id is
  correct and visible to your token.