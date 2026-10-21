#!/usr/bin/env python3
"""Pull the default branch (main, falling back to master) for a set of git repositories.

Runs on Windows, macOS and Linux. Each repo is processed individually with clear markers so
progress is visible when the script runs as a background process. Dirty repos are skipped and
never stashed or cleaned automatically.

Repositories come from --repo-file (one path per line, '#' comments ignored), one or more
--repo flags, or stdin. --scan regenerates the repo list instead of pulling.

Examples
--------
    python3 git_pull.py --repo-file repos.txt --exclude abelson
    python3 git_pull.py --repo /ws/repo-a --repo /ws/repo-b
    git_pull.py --scan /workspace/git --depth 3 --write repos.txt
"""

import argparse
import os
import re
import subprocess
import sys


MARKER_REPO = "===REPO==="
MARKER_DONE = "===DONE==="


def git(repo, *args):
    """Run a git command inside repo and return (returncode, combined output)."""
    done = subprocess.run(
        ["git", "-C", repo] + list(args),
        capture_output=True, text=True, errors="replace",
    )
    return done.returncode, (done.stdout + done.stderr).strip()


def has_local_branch(repo, name):
    code, _ = git(repo, "show-ref", "--verify", "--quiet", "refs/heads/" + name)
    return code == 0


def default_branch(repo):
    """main wins over master; never assume master without checking main first."""
    for candidate in ("main", "master"):
        if has_local_branch(repo, candidate):
            return candidate
    return None


def pull_repo(repo):
    """Pull one repo. Returns a status string used for the run summary."""
    code, dirty = git(repo, "status", "--porcelain")
    if code != 0:
        print("  NOT_A_REPO")
        return "failed"
    if dirty:
        print("  DIRTY - skipping")
        for line in dirty.splitlines():
            print("    " + line)
        return "skipped"

    _, current = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    target = default_branch(repo)
    if not target:
        print("  NO_DEFAULT_BRANCH (on {0})".format(current))
        return "skipped"

    if current != target:
        code, output = git(repo, "checkout", target)
        if code != 0:
            print("  CHECKOUT_FAILED to {0}".format(target))
            for line in output.splitlines():
                print("    " + line)
            return "failed"

    code, output = git(repo, "pull")
    if code != 0 and "ref" in output.lower():
        # Stale ref locks clear after a gc; retry once.
        git(repo, "gc", "--prune=now")
        code, output = git(repo, "pull")
    if code != 0:
        print("  PULL_FAILED on {0}".format(target))
        for line in output.splitlines():
            print("    " + line)
        return "failed"

    last = output.splitlines()[-1] if output else ""
    print("  OK ({0}): {1}".format(target, last))
    return "pulled"


BACKTICK_PATH = re.compile(r"`([^`]+)`")


def paths_in_line(line):
    """Extract repo paths from one line of a plain-text or markdown index.

    The workspace repo index is a markdown steering file that quotes absolute paths in
    backticks, so the same --repo-file reads both formats and no second plain-text copy
    of the list has to exist.
    """
    entry = line.strip()
    if not entry or entry.startswith("#"):
        return []
    quoted = [match.group(1).strip() for match in BACKTICK_PATH.finditer(entry)]
    if quoted:
        return [path for path in quoted if os.path.isabs(path)]
    # Plain-text indexes list one absolute path per line; anything else is prose.
    return [entry] if os.path.isabs(entry) else []


def collect_repos(args):
    repos = []
    if args.repo_file:
        if not os.path.isfile(args.repo_file):
            print("repo file not found: " + args.repo_file)
            sys.exit(1)
        with open(args.repo_file, encoding="utf-8") as handle:
            for line in handle:
                repos.extend(paths_in_line(line))
    for value in args.repo or []:
        # Accept comma-joined values so a single argument behaves like a list.
        repos.extend(part.strip() for part in value.split(",") if part.strip())
    if not repos and not sys.stdin.isatty():
        repos.extend(line.strip() for line in sys.stdin if line.strip()
                     and not line.strip().startswith("#"))
    return repos


def find_repos(root, max_depth):
    """Yield every git repository under root, without descending into one."""
    root = os.path.abspath(root)
    found = []
    for current, dirs, _ in os.walk(root):
        depth = current[len(root):].count(os.sep)
        if ".git" in dirs:
            found.append(current)
            dirs[:] = []
            continue
        if depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
    return sorted(found)


def cmd_scan(args):
    repos = []
    for root in args.scan:
        repos.extend(find_repos(root, args.depth))
    repos = sorted(set(repos))
    lines = ["# git repo index generated by git_pull.py --scan " + " ".join(args.scan),
             "# machine-specific absolute paths; regenerate after adding or moving a repo"]
    lines += repos
    text = "\n".join(lines) + "\n"
    if args.write:
        with open(args.write, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("wrote {0} repositories to {1}".format(len(repos), args.write))
    else:
        sys.stdout.write(text)
    return 0


def cmd_pull(args):
    repos = collect_repos(args)
    if not repos:
        print("no repositories provided: use --repo, --repo-file, or pipe paths in")
        return 1

    excludes = []
    for value in args.exclude or []:
        excludes.extend(part.strip().lower() for part in value.split(",") if part.strip())

    tally = {"pulled": 0, "skipped": 0, "failed": 0, "excluded": 0, "missing": 0}
    for repo in repos:
        print("{0} {1}".format(MARKER_REPO, repo))
        if any(token in repo.lower() for token in excludes):
            print("  EXCLUDED")
            tally["excluded"] += 1
        elif not os.path.isdir(repo):
            print("  MISSING")
            tally["missing"] += 1
        else:
            tally[pull_repo(repo)] += 1

    print(MARKER_DONE)
    print("pulled={pulled} skipped={skipped} failed={failed} "
          "excluded={excluded} missing={missing}".format(**tally))
    return 1 if tally["failed"] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", action="append", help="repository path (repeatable)")
    parser.add_argument("--repo-file", help="file with one repository path per line")
    parser.add_argument("--exclude", action="append",
                        help="skip repos whose path contains this (case-insensitive, repeatable)")
    parser.add_argument("--scan", metavar="ROOT", action="append",
                        help="list git repositories under ROOT instead of pulling (repeatable)")
    parser.add_argument("--depth", type=int, default=3, help="max scan depth (default 3)")
    parser.add_argument("--write", metavar="FILE", help="write the scan result to FILE")
    args = parser.parse_args()
    sys.exit(cmd_scan(args) if args.scan else cmd_pull(args))


if __name__ == "__main__":
    main()