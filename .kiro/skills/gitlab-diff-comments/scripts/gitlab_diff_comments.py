#!/usr/bin/env python3
"""Post code review comments anchored to lines in a GitLab merge request diff.

The GitLab MCP `create_merge_request_note` tool has no `position` parameter and cannot
anchor a note to a diff line, so comments are posted through `glab api` with an explicit
position object.

Subcommands
-----------
anchors : list every added (+) line of a diff with its new-file line number. Comment
          anchors must point at one of these; an unchanged line is rejected by GitLab or
          silently lands in the wrong place.
post    : post one discussion per comment, optionally validating anchors first.

Examples
--------
    python3 gitlab_diff_comments.py anchors --git-range origin/master...HEAD --repo /path/to/repo
    python3 gitlab_diff_comments.py anchors --git-range origin/main...HEAD --filter SignalDownload
    python3 gitlab_diff_comments.py post --project group/sub/repo --mr 323 \
        --comments comments.json --git-range origin/master...HEAD --dry-run

Comments file format (JSON)
---------------------------
    [
      {"file": "src/main/java/Foo.java", "line": 84, "body": "Markdown comment body."},
      {"file": "src/api/foo.ts", "line": 21, "body": "Another one."}
    ]
"""

import argparse
import json
import subprocess
import sys
import urllib.parse


def fail(message):
    """Report a fatal problem on stdout, since stderr is unreliable on some shells."""
    print(message)
    sys.exit(1)


# --------------------------------------------------------------------------- diff parsing

HEADER_PREFIXES = (
    "diff --git", "index ", "old mode", "new mode", "similarity index",
    "rename from", "rename to", "deleted file mode", "new file mode", "Binary files",
)


def parse_added_lines(diff_text):
    """Yield (path, new_line, text) for every added line in a unified diff."""
    path = None
    line_no = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            path, in_hunk = None, False
        elif raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                path = None
            elif target.startswith("b/"):
                path = target[2:]
            else:
                path = target
        elif raw.startswith("@@"):
            parts = raw.split("@@")
            if len(parts) < 2:
                continue
            plus = [tok for tok in parts[1].split() if tok.startswith("+")]
            if not plus:
                continue
            line_no = int(plus[0][1:].split(",")[0]) - 1
            in_hunk = True
        elif raw.startswith(HEADER_PREFIXES):
            continue
        elif in_hunk and path:
            if raw.startswith("+"):
                line_no += 1
                yield path, line_no, raw[1:]
            elif raw.startswith("-") or raw.startswith("\\"):
                continue
            else:
                line_no += 1


def load_diff(args):
    if args.diff_file:
        with open(args.diff_file, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    cmd = ["git"]
    if args.repo:
        cmd += ["-C", args.repo]
    cmd += ["diff", args.git_range]
    done = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if done.returncode != 0:
        fail("git diff failed: " + (done.stderr or "").strip())
    return done.stdout


# --------------------------------------------------------------------------- glab helpers

def glab(api_args, stdin=None):
    try:
        done = subprocess.run(
            ["glab"] + api_args, input=stdin,
            capture_output=True, text=True, errors="replace",
        )
    except FileNotFoundError:
        fail("glab not found on PATH. Install the GitLab CLI and run: glab auth login")
    return done.returncode, done.stdout, done.stderr


def encode_project(project):
    """Numeric ids pass through; full paths are URL-encoded for the API path."""
    return urllib.parse.quote(project, safe="") if "/" in project else project


def fetch_diff_refs(project, mr):
    code, out, err = glab(["api", "projects/{0}/merge_requests/{1}".format(project, mr)])
    if code != 0:
        fail("could not read merge request: " + (err or out).strip())
    refs = json.loads(out).get("diff_refs") or {}
    missing = [k for k in ("base_sha", "start_sha", "head_sha") if not refs.get(k)]
    if missing:
        fail("merge request is missing diff_refs: " + ", ".join(missing))
    return refs


def post_comment(project, mr, refs, comment):
    path = comment["file"]
    payload = {
        "body": comment["body"],
        "position": {
            "base_sha": refs["base_sha"],
            "start_sha": refs["start_sha"],
            "head_sha": refs["head_sha"],
            "position_type": "text",
            "new_path": path,
            "old_path": comment.get("old_path", path),
            "new_line": comment["line"],
        },
    }
    endpoint = "projects/{0}/merge_requests/{1}/discussions".format(project, mr)
    # The Content-Type header is required: without it the API rejects the body with
    # "The provided content-type '' is not supported".
    code, out, err = glab(
        ["api", "--method", "POST", endpoint,
         "--header", "Content-Type: application/json", "--input", "-"],
        stdin=json.dumps(payload),
    )
    if code != 0:
        return False, (err or out).strip()
    try:
        note = json.loads(out)["notes"][0]
    except (ValueError, KeyError, IndexError):
        return False, "unexpected response: " + out[:200]
    if note.get("type") != "DiffNote":
        return False, "created as {0}, not a DiffNote".format(note.get("type"))
    landed = note.get("position", {}).get("new_line")
    if landed != comment["line"]:
        return False, "anchored to line {0}, expected {1}".format(landed, comment["line"])
    return True, note.get("id")


# --------------------------------------------------------------------------- subcommands

def cmd_anchors(args):
    rows = list(parse_added_lines(load_diff(args)))
    if args.filter:
        needle = args.filter.lower()
        rows = [r for r in rows if needle in r[0].lower() or needle in r[2].lower()]
    for path, line, text in rows:
        print("{0}\t{1}\t{2}".format(path, line, text.rstrip()))
    print("{0} added lines".format(len(rows)))
    return 0


def cmd_post(args):
    with open(args.comments, encoding="utf-8") as handle:
        comments = json.load(handle)
    for index, comment in enumerate(comments):
        for field in ("file", "line", "body"):
            if field not in comment:
                fail("comment {0} is missing {1}".format(index, field))

    if args.git_range or args.diff_file:
        valid = {(path, line) for path, line, _ in parse_added_lines(load_diff(args))}
        bad = [c for c in comments if (c["file"], c["line"]) not in valid]
        if bad:
            for comment in bad:
                print("INVALID ANCHOR {0}:{1} is not an added line in this diff".format(
                    comment["file"], comment["line"]))
            print("refusing to post: fix the anchors above")
            return 1
        print("all {0} anchors verified against the diff".format(len(comments)))
    else:
        print("WARNING: anchors not validated. Pass --git-range or --diff-file to check them.")

    if args.dry_run:
        for comment in comments:
            print("DRY-RUN {0}:{1}".format(comment["file"], comment["line"]))
        return 0

    project = encode_project(args.project)
    refs = fetch_diff_refs(project, args.mr)

    failures = 0
    for comment in comments:
        ok, detail = post_comment(project, args.mr, refs, comment)
        label = "OK  " if ok else "FAIL"
        print("{0} {1}:{2} {3}".format(label, comment["file"], comment["line"], detail))
        if not ok:
            failures += 1
    print("{0} posted, {1} failed".format(len(comments) - failures, failures))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_diff_source(sub, required):
        group = sub.add_mutually_exclusive_group(required=required)
        group.add_argument("--git-range", help="git revision range, e.g. origin/master...HEAD")
        group.add_argument("--diff-file", help="file containing a unified diff")
        sub.add_argument("--repo", help="path to the repository (defaults to cwd)")

    anchors = subparsers.add_parser("anchors", help="list added lines usable as comment anchors")
    add_diff_source(anchors, required=True)
    anchors.add_argument("--filter", help="only show lines whose path or text contains this")
    anchors.set_defaults(func=cmd_anchors)

    post = subparsers.add_parser("post", help="post diff-anchored comments")
    post.add_argument("--project", required=True, help="numeric project id or full path")
    post.add_argument("--mr", required=True, type=int, help="merge request iid")
    post.add_argument("--comments", required=True, help="JSON file of comments")
    add_diff_source(post, required=False)
    post.add_argument("--dry-run", action="store_true", help="validate anchors without posting")
    post.set_defaults(func=cmd_post)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()