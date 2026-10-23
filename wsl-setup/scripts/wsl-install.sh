#!/usr/bin/env sh
# wsl-install.sh
# Reproduce the WSL side of the IntelliJ MCP relay on a fresh WSL install.
# Run from inside WSL:  sh ./scripts/wsl-install.sh
#
# Idempotent: safe to re-run. It installs socat, copies the relay script into
# ~/.local/bin, adds a startup hook to ~/.zshrc (and ~/.bashrc if present), and
# installs a per-minute cron job that keeps the relay pointed at IntelliJ's
# live port.
#
# PREREQUISITE (Windows, one-time): run scripts/windows-portproxy-setup.ps1 in
# an elevated PowerShell first, otherwise the relay has nothing to reach.

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RELAY_SRC="$SCRIPT_DIR/intellij-mcp-relay.sh"
RELAY_DST="$HOME/.local/bin/intellij-mcp-relay.sh"

if [ ! -f "$RELAY_SRC" ]; then
  echo "install: cannot find $RELAY_SRC" >&2
  exit 1
fi

# 1) Dependencies. socat does the relay; curl/iproute2 are used for discovery.
echo "==> Installing dependencies (socat, curl, iproute2)..."
if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y socat curl iproute2
else
  echo "install: no apt found; install socat, curl and iproute2 manually." >&2
fi

# 2) Deploy the relay script.
echo "==> Installing relay script to $RELAY_DST..."
mkdir -p "$HOME/.local/bin"
cp "$RELAY_SRC" "$RELAY_DST"
chmod +x "$RELAY_DST"

# 3) Startup hook. Add to whichever shell rc files exist. The guard line is
#    idempotent, so adding it twice is avoided by the grep check.
HOOK_MARK="intellij-mcp-relay.sh"
HOOK_BLOCK='
# Start IntelliJ MCP relay (WSL loopback -> Windows host) if not already running.
# Script is idempotent; safe to call on every shell start.
[ -x "$HOME/.local/bin/intellij-mcp-relay.sh" ] && "$HOME/.local/bin/intellij-mcp-relay.sh"'

for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  [ -f "$rc" ] || continue
  if grep -q "$HOOK_MARK" "$rc"; then
    echo "==> Startup hook already present in $rc"
  else
    echo "==> Adding startup hook to $rc"
    printf '%s\n' "$HOOK_BLOCK" >> "$rc"
  fi
done

# 4) Cron: keep the relay pointed at the live port every minute. The relay
#    early-exits when already correct, so this is cheap.
echo "==> Installing per-minute cron job..."
CRON_LINE="* * * * * $RELAY_DST >> /tmp/intellij-mcp-relay.cron.log 2>&1"
( crontab -l 2>/dev/null | grep -v "$RELAY_DST"; echo "$CRON_LINE" ) | crontab -

# cron is not started automatically on WSL unless systemd or a boot command is
# enabled. Start it if it is not running.
if ! pgrep -x cron >/dev/null 2>&1; then
  echo "==> cron not running; starting it (sudo service cron start)..."
  sudo service cron start || echo "install: could not start cron; enable systemd or start it manually."
fi

# 5) First run to bind the relay now.
echo "==> Running the relay once..."
"$RELAY_DST" || true

cat <<'EOF'

Done.

Next steps (manual, one-time):
  1. Ensure scripts/windows-portproxy-setup.ps1 was run on Windows (elevated).
  2. Open your project in IntelliJ with the MCP server enabled.
  3. Add the intellij-mpc-server entry to ~/.kiro/settings/mcp.json
     (see mcp.json.example in this directory).
  4. Restart `kiro-cli chat`.

Verify:
  ss -ltnp | grep 64392
  curl -sS -m 5 -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:64392/stream   # expect 200
EOF
