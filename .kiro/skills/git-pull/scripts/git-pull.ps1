<#
.SYNOPSIS
  Pull the default branch (main, falling back to master) for a set of git repositories.

.DESCRIPTION
  Processes each repo individually inside a single loop, printing clear markers so
  progress is visible when run as a background process. Dirty repos are skipped
  (never stashed or cleaned automatically).

.PARAMETER Repo
  One or more repository paths. Can also be piped in.

.PARAMETER RepoFile
  Path to a text file containing one repository path per line.
  Blank lines and lines starting with '#' are ignored.

.PARAMETER Exclude
  Repository paths (or substrings) to skip. Matching is case-insensitive and
  substring-based, so '-Exclude abelson' skips any repo whose path contains 'abelson'.

.EXAMPLE
  # Explicit list
  .\git-pull.ps1 -Repo 'c:\ws\repo-a','c:\ws\repo-b'

.EXAMPLE
  # From a file, excluding one domain
  .\git-pull.ps1 -RepoFile .\repos.txt -Exclude 'abelson'

.EXAMPLE
  # Piped
  Get-Content repos.txt | .\git-pull.ps1
#>
[CmdletBinding()]
param(
  [Parameter(ValueFromPipeline = $true, Position = 0)]
  [string[]] $Repo,

  [string] $RepoFile,

  [string[]] $Exclude = @()
)

begin {
  $repos = [System.Collections.Generic.List[string]]::new()

  # Split on commas so a single comma-joined string (e.g. when the script is
  # invoked via `powershell -File`) is treated the same as a PowerShell array.
  function Add-Repos([string[]] $values) {
    foreach ($v in $values) {
      if (-not $v) { continue }
      foreach ($part in ($v -split ',')) {
        $t = $part.Trim()
        if ($t) { $repos.Add($t) }
      }
    }
  }

  if ($RepoFile) {
    if (-not (Test-Path $RepoFile)) { throw "RepoFile not found: $RepoFile" }
    Get-Content $RepoFile |
      ForEach-Object { $_.Trim() } |
      Where-Object { $_ -and -not $_.StartsWith('#') } |
      ForEach-Object { $repos.Add($_) }
  }
}

process {
  if ($Repo) { Add-Repos $Repo }
}

end {
  if ($repos.Count -eq 0) { throw "No repositories provided. Use -Repo, -RepoFile, or pipe paths in." }

  $excludes = @()
  foreach ($e in $Exclude) { if ($e) { $excludes += ($e -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }) } }

  foreach ($r in $repos) {
    Write-Output "===REPO=== $r"

    $skip = $false
    foreach ($ex in $excludes) {
      if ($ex -and $r.ToLower().Contains($ex.ToLower())) { $skip = $true; break }
    }
    if ($skip) { Write-Output "  EXCLUDED"; continue }

    if (-not (Test-Path $r)) { Write-Output "  MISSING"; continue }

    Set-Location $r
    $dirty = git status --porcelain
    if (-not [string]::IsNullOrWhiteSpace($dirty)) {
      Write-Output "  DIRTY - skipping"
      $dirty -split "`n" | ForEach-Object { Write-Output "    $_" }
      continue
    }

    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    $target = $null
    git show-ref --verify --quiet refs/heads/main
    if ($LASTEXITCODE -eq 0) { $target = 'main' }
    else {
      git show-ref --verify --quiet refs/heads/master
      if ($LASTEXITCODE -eq 0) { $target = 'master' }
    }
    if ($null -eq $target) { Write-Output "  NO_DEFAULT_BRANCH (on $branch)"; continue }

    if ($branch -ne $target) {
      git checkout $target 2>&1 | Out-Null
      if ($LASTEXITCODE -ne 0) { Write-Output "  CHECKOUT_FAILED to $target"; continue }
    }

    $pull = git pull 2>&1
    if ($LASTEXITCODE -ne 0) {
      # Retry once after gc for ref lock errors.
      if ($pull -match 'ref') {
        git gc --prune=now 2>&1 | Out-Null
        $pull = git pull 2>&1
      }
    }
    if ($LASTEXITCODE -ne 0) {
      Write-Output "  PULL_FAILED on $target"
      $pull | ForEach-Object { Write-Output "    $_" }
    } else {
      Write-Output "  OK ($target): $(($pull | Select-Object -Last 1))"
    }
  }

  Write-Output "===DONE==="
}
