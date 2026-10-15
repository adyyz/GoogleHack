# Portable uv + managed CPython, scoped to Genesis. No system PATH/registry changes.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonVersion = (Get-Content -LiteralPath (Join-Path $projectRoot '.python-version') -Raw).Trim()
if ($pythonVersion -notmatch '^3\.12\.\d+$') { throw 'Expected a pinned Python 3.12 patch version.' }
$uvRoot = Join-Path $projectRoot '.tools/uv'
$downloads = Join-Path $projectRoot '.cache/downloads'
New-Item -ItemType Directory -Force -Path $uvRoot, $downloads | Out-Null
$uvCommand = Get-ChildItem -LiteralPath $uvRoot -Recurse -Filter uv.exe -File | Select-Object -First 1
if (-not $uvCommand) {
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/astral-sh/uv/releases/tags/0.13.1'
    $asset = $release.assets | Where-Object { $_.name -eq 'uv-x86_64-pc-windows-msvc.zip' } | Select-Object -First 1
    if (-not $asset) { throw 'Official uv Windows archive not found.' }
    $archive = Join-Path $downloads $asset.name
    Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $archive
    $expectedHash = if ($asset.digest -match '^sha256:([a-f0-9]{64})$') { $Matches[1] } else { $null }
    if (-not $expectedHash) {
        $checksumAsset = $release.assets | Where-Object { $_.name -eq ($asset.name + '.sha256') } | Select-Object -First 1
        if (-not $checksumAsset) { throw 'Official checksum metadata not found.' }
        $checksum = (Invoke-WebRequest -UseBasicParsing -Uri $checksumAsset.browser_download_url).Content
        if ($checksum -notmatch '[a-fA-F0-9]{64}') { throw 'Invalid checksum metadata.' }
        $expectedHash = $Matches[0]
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) { throw 'uv archive checksum mismatch.' }
    Expand-Archive -LiteralPath $archive -DestinationPath $uvRoot
    @{version='0.13.1';url=$asset.browser_download_url;sha256=$expectedHash} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $projectRoot '.tools/uv-download.json') -Encoding UTF8
    $uvCommand = Get-ChildItem -LiteralPath $uvRoot -Recurse -Filter uv.exe -File | Select-Object -First 1
}
if (-not $uvCommand) { throw 'uv executable missing after extraction.' }
$env:UV_CACHE_DIR = Join-Path $projectRoot '.cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectRoot '.tools/python'
$env:UV_PYTHON_BIN_DIR = Join-Path $projectRoot '.tools/python-bin'
$env:UV_PYTHON_INSTALL_REGISTRY = 'false'
$env:UV_PYTHON_NO_REGISTRY = 'true'
$env:UV_NO_MODIFY_PATH = '1'
& $uvCommand.FullName python install $pythonVersion
if ($LASTEXITCODE -ne 0) { throw 'Managed Python installation failed.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.venv/Scripts/python.exe'))) {
    & $uvCommand.FullName venv --python $pythonVersion .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& (Join-Path $projectRoot '.venv/Scripts/python.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Python verification failed.' }
Write-Output 'Python environment ready under Genesis/.venv; run npm run python:sync to install the locked application packages.'
