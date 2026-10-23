# WSL2 + Kiro CLI + IntelliJ MCP — reproducible setup

Kiro CLI runs inside **WSL2 (Ubuntu)**; IntelliJ IDEA runs as a **Windows** app.
This directory reproduces the whole working setup on a fresh WSL install.

All Kiro MCP config lives in `~/.kiro/settings/mcp.json` (hot-reloaded; restart
`kiro-cli chat` if a server sticks on "loading").

## Contents

```
wsl-setup/
├── README.md                          # this runbook
├── mcp.json.example                   # the intellij-mpc-server entry to merge into ~/.kiro/settings/mcp.json
└── scripts/
    ├── windows-portproxy-setup.ps1    # Windows, elevated, ONE-TIME
    ├── intellij-mcp-relay.sh          # WSL relay with dynamic port discovery
    └── wsl-install.sh                 # WSL installer (deps + relay + zshrc hook + cron)
```

## TL;DR — fresh install

1. **Windows (elevated PowerShell), once:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File \\wsl.localhost\Ubuntu\home\<user>\...\wsl-setup\scripts\windows-portproxy-setup.ps1
   ```
   (or copy the `.ps1` to Windows and run it there).

2. **WSL:**
   ```sh
   sh ./scripts/wsl-install.sh
   ```

3. Merge `mcp.json.example` into `~/.kiro/settings/mcp.json`.

4. Open your project in IntelliJ with the MCP server enabled, then restart
   `kiro-cli chat`.

5. Verify:
   ```sh
   curl -sS -m 5 -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:64392/stream   # expect 200
   ```

---

## Why it is built this way (the root causes)

**IntelliJ's MCP server binds where the IDE *process* runs — Windows loopback.**
Even when the project files and the project JDK live in WSL, and even when IntelliJ
spawns Linux helpers into WSL (the Maven server, the Junie agent), the IDE core is
still the Windows process, so its built-in web server listens on Windows
`127.0.0.1` only. That server also only accepts requests whose `Host` header is
`localhost`/`127.0.0.1`.

Two consequences drive the whole design:

1. **WSL cannot reach a Windows-loopback socket directly.** Something on the
   **Windows** side must expose it to the WSL-facing interface. A WSL-only script
   cannot cross this boundary — this is why a Windows portproxy is required.
   (Confirmed in practice: the port showed as refused/closed from WSL until the
   portproxy was added.)

2. **IntelliJ's port is not fixed.** The built-in server starts at **64342** and
   increments (64343, 64344, …) when a port is already taken. The chosen port is
   reused in later sessions but changes across IDE/WSL restarts and version bumps.
   (This is exactly why the setup broke after a WSL restart: the old hardcoded port
   became a dead target.)

The design handles both: a **one-time Windows portproxy** exposes the whole range
to WSL (persists across reboots), and a **WSL relay auto-discovers** the live port
each run and maps it to a **fixed local port (64392)** so `mcp.json` never changes.

```
Kiro (WSL)  ->  127.0.0.1:64392  ->  socat relay  ->  <gateway>:<live port>
                (fixed, in mcp.json)                   (Windows portproxy -> 127.0.0.1:<live port> -> IntelliJ)
```

---

## Step 1 — Windows portproxy (one-time)

Run `scripts/windows-portproxy-setup.ps1` in an **elevated** PowerShell on Windows.
It forwards `64342-64550` from `0.0.0.0` to Windows `127.0.0.1` and opens the
firewall. `netsh` portproxy rules and the firewall rule **persist across reboots**,
so this is genuinely one-time.

Inspect / remove later:
```powershell
netsh interface portproxy show all
# netsh interface portproxy delete v4tov4 listenport=<p> listenaddress=0.0.0.0
# Remove-NetFirewallRule -DisplayName "IntelliJ MCP range from WSL"
```

## Step 2 — WSL relay + cron (per fresh install)

Run `scripts/wsl-install.sh` inside WSL. It:

1. installs `socat`, `curl`, `iproute2`;
2. copies `intellij-mcp-relay.sh` to `~/.local/bin/` and makes it executable;
3. adds a startup hook to `~/.zshrc` (and `~/.bashrc` if present):
   ```sh
   [ -x "$HOME/.local/bin/intellij-mcp-relay.sh" ] && "$HOME/.local/bin/intellij-mcp-relay.sh"
   ```
4. installs a **per-minute cron** job so the relay re-points itself if IntelliJ's
   port changes mid-session:
   ```
   * * * * * /home/<user>/.local/bin/intellij-mcp-relay.sh >> /tmp/intellij-mcp-relay.cron.log 2>&1
   ```
5. starts `cron` if it is not already running (WSL does not start it automatically
   unless systemd or a boot command is enabled).

### How the relay finds the port (and why it is fast)

The portproxy forwards the **whole range** to Windows loopback, so every port in
`64342-64550` accepts TCP instantly; only the HTTP response distinguishes IntelliJ.
A lower connect-timeout therefore does not help. The relay instead:

- **caches** the last-known-good port (`/tmp/socat-mcp.port`) and tries it first —
  one probe in the common case, since IntelliJ reuses its port;
- on a miss, **probes the whole range in parallel** and takes the first HTTP `200`.

This took a cold scan from **~2 minutes** (sequential) down to **~0.2 s**. The
once-per-minute cron is cheap because the relay early-exits when it is already
pointed at the live port.

## Step 3 — Kiro config

Merge `mcp.json.example` into `~/.kiro/settings/mcp.json`. The key points:

```json
"intellij-mpc-server": {
  "url": "http://127.0.0.1:64392/stream",
  "headers": {},
  "disabled": false
}
```

- Use the `/stream` endpoint, **not** `/sse`, and no `type` field. Kiro uses
  Streamable HTTP (POST); IntelliJ answers `405` on `POST /sse` but `200` on
  `/stream`.
- The URL stays on the **fixed** local port 64392 forever — the relay tracks the
  moving remote port, not `mcp.json`.

---

## Verify end to end

```sh
# relay listening on the fixed local port
ss -ltnp | grep 64392

# HTTP 200 through the relay
curl -sS -m 5 -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:64392/stream

# full MCP initialize (should return serverInfo: IntelliJ IDEA MCP Server)
curl -sS -m 6 -X POST http://127.0.0.1:64392/stream \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"kiro","version":"1"}}}'
```

In Kiro, run `/mcp` to confirm `intellij-mpc-server` is connected.

---

## Troubleshooting (things that actually bit us)

**"IntelliJ MCP is failing after a WSL restart."**
The port moved. The relay + cron handle this automatically; force it with
`~/.local/bin/intellij-mcp-relay.sh`. If nothing is found, IntelliJ is closed, its
MCP server is disabled, or the Windows portproxy is missing.

**Relay listening on 64392 but HTTP times out with an empty reply.**
socat is pointed at a stale remote port (IntelliJ moved). Re-run the relay; it
rebinds to the discovered port. The cron does this within a minute.

**Probe returns `403` instead of `200`.**
The `Host` header was the gateway IP. IntelliJ's built-in server only accepts
`Host: localhost`/`127.0.0.1`. The relay works because Kiro connects to
`127.0.0.1:64392`, so the forwarded request already carries a loopback Host; the
discovery probe sets `Host: 127.0.0.1:<port>` explicitly for the same reason.

**Running the relay SIGTERMs the shell / "Terminated".**
Never `pkill -f "TCP-LISTEN:..."` — that pattern matches the shell that sourced the
script too. Kill socat by exact name: `pkill -x socat`.

**Kiro prompts for authentication, but the IntelliJ server has no auth.**
The IntelliJ MCP server is unauthenticated (no OAuth discovery, no
`WWW-Authenticate`, bare `initialize` returns 200). Kiro *speculatively* starts an
OAuth redirect server "in case the server requires OAuth" and only falls into that
path when the **connection fails** (logged as `error: "fetch failed"`). So the auth
prompt is a symptom of a failed/stale connection from a session that started before
the relay was healthy. **Fix: restart `kiro-cli chat`** once the endpoint returns
200. Do **not** add a token — the server does not want one. (Kiro caches abandoned
OAuth flows per server in `~/.kiro/secrets.json` as `kiro.mcp.<hash>.{discovery,
client,verifier[,tokens]}`; entries without `tokens` are incomplete speculative
flows. A clean reconnect supersedes them; avoid hand-deleting since the hash is not
a plain URL SHA and you could clobber a real OAuth server such as atlassian.)

**If IntelliJ ever picks a port outside `64342-64550`.**
Widen both the Windows loop (`windows-portproxy-setup.ps1`) and `SCAN_END` in
`intellij-mcp-relay.sh`.

### General
- Run `/mcp` in Kiro to see each server's status.
- Kiro logs: `~/.kiro/logs/<timestamp>/` (`kiro.log`, `mcp.log`).
- Relay logs: `/tmp/socat-mcp.log` (socat) and `/tmp/intellij-mcp-relay.cron.log` (cron).

---

## Alternative: run IntelliJ *in* WSL (no Windows bridge at all)

JetBrains **Remote Development → WSL** runs the IDE backend as a Linux process in
WSL, so the MCP server binds on WSL `127.0.0.1` and Kiro reaches it directly — no
portproxy, no socat, no cron. Point `mcp.json` at
`http://127.0.0.1:<discovered>/stream`. (WSL *mirrored* networking would also expose
Windows loopback directly, but it changes all WSL networking and can break
Docker/VPN, so it is avoided here.)

---

## Other MCP servers (for completeness)

### GitLab MCP server (self-managed)
- Requires the corporate VPN. If it is down, the server fails to connect.
- Auth is OAuth (browser flow via `/mcp`) or a **fine-grained** personal access
  token with the **MCP tool** resource and **Execute** permission. Legacy PATs,
  project and group tokens are rejected (`403 insufficient_scope`).
- Keep the token out of `mcp.json` — reference an env var:
  ```json
  "gitlab-entain": {
    "url": "https://git.entaingroup.com/api/v4/mcp",
    "headers": { "Authorization": "Bearer ${GITLAB_MCP_TOKEN}" },
    "disabled": false
  }
  ```
  Set `export GITLAB_MCP_TOKEN='<token>'` in the shell that launches Kiro, then
  restart `kiro-cli chat`.

### git, fetch, maven (uvx-launched)
Ubuntu 24.04 has no `uv` apt package; install via `pipx`:
```bash
sudo apt update && sudo apt install -y pipx
pipx install uv
uvx --version
```
`pipx` puts `uv`/`uvx` in `~/.local/bin` (must be on `PATH`). First start downloads
each package.
```json
"fetch": { "command": "uvx", "args": ["mcp-server-fetch"] },
"git":   { "command": "uvx", "args": ["mcp-server-git"] },
"maven": { "command": "uvx", "args": ["maven-mcp-server@latest"] }
```

### Secrets
Keep tokens out of `mcp.json`: reference environment variables (`${VAR}`) in
`headers`/`env`. Applies to the Atlassian `Authorization` header too.
