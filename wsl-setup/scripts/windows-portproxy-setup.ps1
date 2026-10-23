# windows-portproxy-setup.ps1
# Run ONCE in an ELEVATED PowerShell on the Windows host (not inside WSL).
#
# IntelliJ (a Windows app) binds its MCP / built-in web server to Windows
# loopback (127.0.0.1) only, so WSL cannot reach it directly. This forwards the
# whole JetBrains built-in-server port range from the WSL-facing interface
# (0.0.0.0) to Windows loopback, and opens the firewall for it.
#
# netsh portproxy rules and the firewall rule PERSIST across reboots, so this is
# genuinely one-time. Re-run only if you widen the range.
#
# IntelliJ picks its port starting at 64342 and increments when one is taken, so
# the range below must cover wherever it may land. Widen it (and SCAN_END in
# intellij-mcp-relay.sh) if IntelliJ ever reports a higher port.

$ErrorActionPreference = 'Stop'

$startPort = 64342
$endPort   = 64550

Write-Host "Adding portproxy rules $startPort-$endPort (0.0.0.0 -> 127.0.0.1)..."
for ($p = $startPort; $p -le $endPort; $p++) {
    netsh interface portproxy add v4tov4 `
        listenport=$p listenaddress=0.0.0.0 `
        connectport=$p connectaddress=127.0.0.1 | Out-Null
}

Write-Host "Adding inbound firewall rule for the range..."
# Remove a prior rule with the same name first so re-runs stay idempotent.
Get-NetFirewallRule -DisplayName "IntelliJ MCP range from WSL" -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "IntelliJ MCP range from WSL" `
    -Direction Inbound -Protocol TCP -LocalPort "$startPort-$endPort" -Action Allow | Out-Null

Write-Host ""
Write-Host "Done. Current portproxy rules:"
netsh interface portproxy show all

Write-Host ""
Write-Host "To remove a single rule later:"
Write-Host "  netsh interface portproxy delete v4tov4 listenport=<p> listenaddress=0.0.0.0"
Write-Host "To remove the firewall rule later:"
Write-Host "  Remove-NetFirewallRule -DisplayName 'IntelliJ MCP range from WSL'"
