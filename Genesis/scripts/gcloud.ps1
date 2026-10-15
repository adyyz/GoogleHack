$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$command = Join-Path $projectRoot '.tools/google-cloud-sdk/bin/gcloud.cmd'
if (-not (Test-Path -LiteralPath $command)) { throw 'Run scripts/install-local-tools.ps1 first.' }
$env:CLOUDSDK_CONFIG = Join-Path $projectRoot '.tools/gcloud-config'
$env:CLOUDSDK_CORE_DISABLE_USAGE_REPORTING = 'true'
& $command @args
exit $LASTEXITCODE
