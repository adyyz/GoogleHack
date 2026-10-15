$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:UV_CACHE_DIR = Join-Path $projectRoot '.cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot '.tools/python'
& (Join-Path $projectRoot '.tools/uv/uv.exe') sync --frozen
exit $LASTEXITCODE
