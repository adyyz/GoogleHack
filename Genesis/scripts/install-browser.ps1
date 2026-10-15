$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectRoot '.cache/playwright'
$nodePath = (Get-Command node -ErrorAction Stop).Source
& $nodePath (Join-Path $projectRoot 'node_modules/@playwright/test/cli.js') install chromium --only-shell
exit $LASTEXITCODE
