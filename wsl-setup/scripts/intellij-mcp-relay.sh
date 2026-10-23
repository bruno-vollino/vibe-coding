#!/usr/bin/env sh
# Relay WSL loopback 127.0.0.1:64392 -> Windows host IntelliJ MCP server.
#
# IntelliJ (the Windows app) auto-picks its built-in server port starting at
# 64342 and incrementing when a port is taken, so the remote port moves between
# sessions. This script DISCOVERS the live port and binds a FIXED local port to
# it, so ~/.kiro/settings/mcp.json never has to change.
#
# Speed: the Windows portproxy forwards the WHOLE range to Windows loopback, so
# every port in the range accepts TCP instantly and only the HTTP response
# distinguishes IntelliJ. A lower connect-timeout therefore does not help; what
# helps is (1) trying the cached last-known port first, and (2) probing the whole
# range in PARALLEL instead of one-by-one. A full cold scan drops from ~2 min to
# a couple of seconds.

LOCAL_PORT=64392
SCAN_START=64342
SCAN_END=64550
PROBE_TIMEOUT=1          # per-probe max seconds (HTTP response wait)
CACHE=/tmp/socat-mcp.port

# cron runs with a minimal PATH. ip lives in /usr/sbin, most tools in /usr/bin;
# set PATH explicitly so this works both from an interactive shell and cron.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

WIN_GW=$(ip route | awk '/^default/{print $3; exit}')
[ -z "$WIN_GW" ] && { echo "intellij-mcp-relay: no gateway" >&2; exit 1; }

# Return 0 if $1 is the live IntelliJ MCP port. Probe with a loopback Host header;
# IntelliJ returns 403 to a gateway-IP Host, 200 to localhost.
is_mcp_port() {
  [ "$(curl -sS -m "$PROBE_TIMEOUT" -H "Host: 127.0.0.1:$1" \
        -o /dev/null -w '%{http_code}' "http://${WIN_GW}:$1/stream" 2>/dev/null)" = "200" ]
}

REMOTE_PORT=""

# 1) Fast path: the port IntelliJ is reused across sessions, so try the cached
#    one first. One probe, instant hit in the common case.
if [ -f "$CACHE" ]; then
  cached=$(cat "$CACHE" 2>/dev/null)
  if [ -n "$cached" ] && is_mcp_port "$cached"; then
    REMOTE_PORT="$cached"
  fi
fi

# 2) Cold path: probe the whole range in parallel, first 200 wins.
if [ -z "$REMOTE_PORT" ]; then
  tmp=$(mktemp -d /tmp/mcp-scan.XXXXXX)
  for p in $(seq "$SCAN_START" "$SCAN_END"); do
    ( is_mcp_port "$p" && echo "$p" > "$tmp/hit.$p" ) &
  done
  wait
  REMOTE_PORT=$(cat "$tmp"/hit.* 2>/dev/null | sort -n | head -1)
  rm -rf "$tmp"
fi

if [ -z "$REMOTE_PORT" ]; then
  echo "intellij-mcp-relay: no MCP server on ${WIN_GW}:${SCAN_START}-${SCAN_END} (IntelliJ open? MCP enabled? portproxy set?)" >&2
  exit 1
fi

echo "$REMOTE_PORT" > "$CACHE"

# If a relay is already pointed at the live port, leave it. Otherwise rebind.
# NOTE: kill socat by exact name (-x), never by a TCP-LISTEN pattern: a pattern
# match also hits the shell that sourced this script and SIGTERMs it.
if ss -tlnp 2>/dev/null | grep -q "127.0.0.1:${LOCAL_PORT}"; then
  grep -q "TCP:${WIN_GW}:${REMOTE_PORT}" /tmp/socat-mcp.cmd 2>/dev/null && exit 0
  pkill -x socat 2>/dev/null
  sleep 2
fi

echo "TCP:${WIN_GW}:${REMOTE_PORT}" > /tmp/socat-mcp.cmd
setsid socat "TCP-LISTEN:${LOCAL_PORT},bind=127.0.0.1,reuseaddr,fork" \
  "TCP:${WIN_GW}:${REMOTE_PORT}" >/tmp/socat-mcp.log 2>&1 &

echo "intellij-mcp-relay: 127.0.0.1:${LOCAL_PORT} -> ${WIN_GW}:${REMOTE_PORT}"
