param(
    [switch]$Apply,
    [switch]$FreeAllowanceVerified
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cloudCli = Join-Path $projectRoot '.tools/google-cloud-sdk/bin/gcloud.cmd'
if (-not (Test-Path -LiteralPath $cloudCli)) { throw 'Install the existing project-local Google Cloud CLI first.' }
$env:CLOUDSDK_CONFIG = Join-Path $projectRoot '.tools/gcloud-config'
$env:CLOUDSDK_CORE_DISABLE_USAGE_REPORTING = 'true'
$projectId = 'genesis-aicb'
$secretId = 'genesis-gemini-api-key'

if (-not $Apply) {
    Write-Output "Plan only: store one Gemini Developer API key in projects/$projectId/secrets/$secretId/versions/1."
    Write-Output 'Apply enables only Secret Manager API if needed, creates this secret with automatic replication, and uploads one version from a masked prompt.'
    Write-Output 'Existing versions are preserved. No IAM changes, billing changes, deployment or model requests are performed.'
    Write-Output 'Before applying: sign in with scripts/gcloud.ps1 auth login and confirm room in the billing account shared allowance (6 active versions, 10,000 accesses/month).'
    Write-Output 'Then run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-gemini-secret.ps1 -Apply -FreeAllowanceVerified'
    exit 0
}
if (-not $FreeAllowanceVerified) { throw 'Verify shared Secret Manager free allowance before using -Apply -FreeAllowanceVerified. Gemini Free Tier does not verify it.' }
$activeAccounts = & $cloudCli auth list --filter=status:ACTIVE --format='value(account)' --quiet
if ($LASTEXITCODE -ne 0 -or -not $activeAccounts) { throw 'No active CLI account. Run scripts/gcloud.ps1 auth login locally first.' }
$actualProjectNumber = & $cloudCli projects describe $projectId --format='value(projectNumber)' --quiet
if ($LASTEXITCODE -ne 0 -or "$actualProjectNumber".Trim() -ne '638299117256') { throw 'Cannot verify the intended genesis-aicb project.' }
$billingEnabled = & $cloudCli billing projects describe $projectId --format='value(billingEnabled)' --quiet
if ($LASTEXITCODE -ne 0 -or "$billingEnabled".Trim().ToLowerInvariant() -ne 'true') { throw 'Linked billing could not be verified. This script will not activate or change billing.' }
$enabledService = & $cloudCli services list --enabled --project=$projectId --filter='config.name:secretmanager.googleapis.com' --format='value(config.name)' --quiet
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect enabled services.' }
if (-not $enabledService) {
    & $cloudCli services enable secretmanager.googleapis.com --project=$projectId --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not enable Secret Manager API.' }
}
$candidateNames = & $cloudCli secrets list --project=$projectId --filter="name:$secretId" --format='value(name)' --quiet
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect existing secret metadata.' }
$existing = @($candidateNames | Where-Object { ($_ -split '/')[-1] -eq $secretId })
if ($existing) {
    $versions = & $cloudCli secrets versions list $secretId --project=$projectId --format='value(name)' --limit=1 --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect existing secret versions.' }
    if ($versions) {
        Write-Output 'Secret already has a version. No payload was read and no duplicate version was uploaded.'
        Write-Output 'Inspect its version metadata in Secret Manager before changing or rotating the key.'
        exit 0
    }
}
$secureKey = Read-Host 'Gemini API key (masked; do not paste it into chat)' -AsSecureString
$keyPointer = [IntPtr]::Zero
$plainKey = $null
try {
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer).Trim()
    if (-not $plainKey -or $plainKey -match '\s') { throw 'An API key without whitespace is required.' }
    if (-not $existing) {
        & $cloudCli secrets create $secretId --project=$projectId --replication-policy=automatic --quiet
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the secret. No key was uploaded.' }
    }
    # Payload goes only to process stdin, never a command argument or local file.
    $versionName = $plainKey | & $cloudCli secrets versions add $secretId --project=$projectId --data-file=- --format='value(name)' --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Key upload did not complete. Inspect version metadata before trying again.' }
    Write-Output "Stored secret version: $versionName"
    Write-Output 'The key was not displayed. Application deployment and Gemini calls remain disabled.'
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    $plainKey = $null
    $secureKey.Dispose()
}
