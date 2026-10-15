param([Parameter(Mandatory=$true)][string]$Repository)
$ErrorActionPreference = 'Stop'
if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw 'Repository must be owner/repo' }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
  if (-not (Test-Path -LiteralPath '.git')) { git init -b main; if ($LASTEXITCODE -ne 0) { throw 'git init failed' } }
  git add index.html assets data scripts tests README.md .gitignore .github
  if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
  git diff --cached --quiet
  if ($LASTEXITCODE -eq 1) { git -c user.name='UT Rental Atlas' -c user.email='atlas@users.noreply.github.com' commit -m 'Build UT Austin rental atlas'; if ($LASTEXITCODE -ne 0) { throw 'commit failed' } }
  $remoteUrl = "https://github.com/$Repository.git"
  $currentRemote = git remote get-url origin 2>$null
  if ($LASTEXITCODE -eq 0 -and $currentRemote -ne $remoteUrl) { throw 'Existing origin differs. Inspect it before publishing.' }
  if ($LASTEXITCODE -ne 0) { git remote add origin $remoteUrl }
  git push -u origin main
  if ($LASTEXITCODE -ne 0) { throw 'Push failed. Verify repository exists and GitHub login has access.' }
} finally { Pop-Location }
