$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
Write-Output "Project root: $projectRoot"
Write-Output "Local-only checks; no authentication, deployment or model calls."

$nodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $nodePath -and (Test-Path -LiteralPath 'C:/Program Files/nodejs/node.exe')) {
    $nodePath = 'C:/Program Files/nodejs/node.exe'
}
if ($nodePath) {
    & $nodePath --version
    $firebasePackage = Join-Path $projectRoot 'node_modules/firebase-tools/package.json'
    if (Test-Path -LiteralPath $firebasePackage) {
        $package = Get-Content -LiteralPath $firebasePackage -Raw | ConvertFrom-Json
        Write-Output "Project Firebase CLI: $($package.version)"
    } else { Write-Output 'Project Firebase CLI: MISSING (run npm ci)' }
} else { Write-Output 'Node.js: MISSING' }

$cloudCandidates = @(
    (Join-Path $projectRoot '.tools/google-cloud-sdk/bin/gcloud.cmd'),
    (Join-Path $env:LOCALAPPDATA 'Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'),
    'C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'
)
$cloudCommand = Get-Command gcloud -ErrorAction SilentlyContinue
if ($cloudCommand) { $cloudPath = $cloudCommand.Source }
else { $cloudPath = $cloudCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1 }
if ($cloudPath) {
    $env:CLOUDSDK_CONFIG = Join-Path $projectRoot '.tools/gcloud-config'
    $env:CLOUDSDK_CORE_DISABLE_USAGE_REPORTING = 'true'
    & $cloudPath --version
} else { Write-Output 'Google Cloud CLI: MISSING' }

$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $pythonPath) { & $pythonPath --version }
else { Write-Output 'Python 3.12 environment: MISSING (run scripts/setup-python.ps1)' }

$javaHome = Get-ChildItem -LiteralPath (Join-Path $projectRoot '.tools/java') -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin/java.exe') } | Select-Object -First 1
$localJava = if ($javaHome) { Join-Path $javaHome.FullName 'bin/java.exe' } else { Join-Path $projectRoot '.tools/java/bin/java.exe' }
$javaCommand = Get-Command java -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $localJava) { & $localJava -version }
elseif ($javaCommand) { & $javaCommand.Source -version }
else { Write-Output 'Java runtime: MISSING (needed by the Firestore emulator)' }

Write-Output 'Cloud credentials/credits: NOT CHECKED by doctor; verify before live operations.'
