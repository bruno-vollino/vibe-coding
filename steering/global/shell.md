---
inclusion: always
---

# Shell & Scripting

Default to commands and scripts that run unchanged on Windows, macOS and Linux. Platform-specific
syntax is a last resort, not a starting point.

## Portability rules

- Prefer cross-platform CLIs (`git`, `glab`, `mvn`, `npm`, `python3`) over shell builtins and
  shell-specific syntax. These behave the same everywhere and keep skills portable.
- When a task needs real logic (parsing, looping, building JSON), put it in a script file under the
  skill's `scripts/` directory instead of chaining inline shell commands. Inline chains are where
  quoting and escaping bugs live.
- Default scripting language for bundled skill scripts: **Python 3, standard library only**. It is
  present on all three platforms and handles JSON, regex and subprocess cleanly without
  dependencies. Invoke as `python3` (falling back to `python` on Windows).
- If a script genuinely must be platform-specific, ship one per platform side by side
  (`scripts/do-thing.ps1` and `scripts/do-thing.sh`) and select by OS. Never leave a skill with only
  a `.ps1`.
- Pass structured data through files, not command-line strings. Write a JSON file and point the tool
  at it (`glab api --input file.json`); this sidesteps every quoting difference between shells.
- Verify an interpreter actually runs before relying on it. On Windows, `python`/`python3` on PATH is
  often the Microsoft Store stub that resolves but does nothing: check `python --version` first.

## Keep commands allow-listable

Agent permission rules match globs against the whole command string, so a long composed pipeline
matches nothing and prompts for approval every time. Prefer a small number of canonical commands:
a bundled script with stable arguments, or a plain `git`/`glab` subcommand. Spell out read-only
intent in the command itself (for example `glab api --method GET ...`) so a read can be allow-listed
without the same pattern also permitting a write.

## Windows (PowerShell)

- The command echo in tool output is mangled (a progressively-typed copy of the command) and the
  reported exit code is `-1` even on success. **Do not trust the exit code**: verify by effect.
- Reading long stdout is unreliable. Redirect output to a file and read it back with the file-reading
  tool rather than parsing it out of the terminal response.
- `&&` is not a valid statement separator in Windows PowerShell 5.x. Use `;`, or separate calls when
  the second command must not run on failure.
- `npm`, `npx` and similar Node shims fail with "running scripts is disabled on this system" because
  `npm.ps1` is blocked by execution policy. Call `npm.cmd` instead.
- Use single-quoted strings and single-quoted here-strings (`@'` ... `'@`) for literal text. Backtick
  is PowerShell's escape character, so double-quoted strings mangle anything containing backticks.
- To write a file with exact content and LF endings:
  `[System.IO.File]::WriteAllText($path, ($text -replace "`r`n", "`n"), (New-Object System.Text.UTF8Encoding($false)))`

## macOS / Linux

- Exit codes and stdout are reliable; `&&`, `||` and pipelines behave normally.
- Target POSIX `sh` where practical so scripts do not depend on bash or zsh specifics.
- Keep bundled scripts executable (`chmod +x`) and give them a `#!/usr/bin/env python3` or
  `#!/usr/bin/env sh` shebang.