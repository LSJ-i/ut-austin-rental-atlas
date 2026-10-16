param([Parameter(Mandatory=$true)][string]$Repository)
$ErrorActionPreference = 'Stop'
if ($Repository -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw 'Repository must be owner/repo' }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
  $freshCheckout = -not (Test-Path -LiteralPath '.git')
  if ($freshCheckout) { git init -b main; if ($LASTEXITCODE -ne 0) { throw 'git init failed' } }
  $remoteUrl = "https://github.com/$Repository.git"
  $remotes = @(git remote)
  if ($remotes -contains 'origin') {
    $currentRemote = git remote get-url origin
    if ($currentRemote -ne $remoteUrl) { throw 'Existing origin differs. Inspect it before publishing.' }
  } else { git remote add origin $remoteUrl }
  if ($freshCheckout) {
    git fetch origin main
    if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch existing main branch. Verify repository and login.' }
    # Newly initialized metadata only: keep every local working file intact.
    git reset --mixed FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize local branch from origin' }
  }
  git add index.html assets data scripts tests docs README.md .gitignore .github
  if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
  git diff --cached --quiet
  if ($LASTEXITCODE -eq 1) { git -c user.name='UT Rental Atlas' -c user.email='atlas@users.noreply.github.com' commit -m 'Build UT Austin rental atlas'; if ($LASTEXITCODE -ne 0) { throw 'commit failed' } }
  git push -u origin main
  if ($LASTEXITCODE -ne 0) { throw 'Push failed. Verify repository exists and GitHub login has access.' }
} finally { Pop-Location }

