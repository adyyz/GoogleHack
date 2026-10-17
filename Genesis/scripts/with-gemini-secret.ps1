param(
    [ValidateSet('Check', 'Api', 'Smoke', 'Worker')][string]$Action = 'Check',
    [ValidatePattern('^[1-9][0-9]*$')][string]$Version = '2',
    [ValidatePattern('^[A-Za-z0-9_-]{1,255}$')][string]$SecretId = 'testing_free_gemini_api',
    [switch]$EnableLocalGemini
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cloudCli = Join-Path $projectRoot '.tools/google-cloud-sdk/bin/gcloud.cmd'
if (-not (Test-Path -LiteralPath $cloudCli)) { throw 'Install the existing project-local Google Cloud CLI first.' }
$env:CLOUDSDK_CONFIG = Join-Path $projectRoot '.tools/gcloud-config'
$env:CLOUDSDK_CORE_DISABLE_USAGE_REPORTING = 'true'
$previousKey = $env:GEMINI_API_KEY
$savedLocalSettings = @{}
foreach ($setting in @('LOCAL_GEMINI_ENABLED', 'LOCAL_GEMINI_FREE_VERIFIED', 'LOCAL_GEMINI_VERIFIED_UNTIL')) {
    $savedLocalSettings[$setting] = [Environment]::GetEnvironmentVariable($setting, 'Process')
}
if ($Action -eq 'Worker' -and -not $EnableLocalGemini) { throw 'Worker requires explicit -EnableLocalGemini; it may make model requests when today''s admin switch is enabled.' }
try {
    # Capture stdout in memory; never emit the secret or write a credential file.
    $payload = & $cloudCli secrets versions access $Version --secret=$SecretId --project=genesis-aicb --quiet
    if ($LASTEXITCODE -ne 0 -or -not $payload) { throw 'Secret access failed. Check CLI sign-in, version state and secret-level access.' }
    $env:GEMINI_API_KEY = ("$payload").Trim()
    $payload = $null
    if ($Action -eq 'Check') {
        Write-Output "Secret access succeeded: projects/genesis-aicb/secrets/$SecretId/versions/$Version. Payload suppressed; no model request sent."
        exit 0
    }
    Set-Location -LiteralPath $projectRoot
    if ($EnableLocalGemini) {
        $env:LOCAL_GEMINI_ENABLED = 'true'
        $env:LOCAL_GEMINI_FREE_VERIFIED = 'true'
        $env:LOCAL_GEMINI_VERIFIED_UNTIL = [DateTime]::UtcNow.AddHours(1).ToString('o')
        Write-Output 'Local Developer API opt-in expires in one hour. Today''s separate admin switch and the 12-attempt daily cap still apply.'
    }
    if ($Action -eq 'Smoke') {
        & (Join-Path $PSScriptRoot 'python.ps1') -m backend.gemini_smoke
    } elseif ($Action -eq 'Worker') {
        & (Join-Path $PSScriptRoot 'python.ps1') -m backend.jobs --once
    } else {
        & (Join-Path $PSScriptRoot 'python.ps1') -m uvicorn backend.api:app --host 127.0.0.1 --port 8080
    }
    $childExitCode = $LASTEXITCODE
}
finally {
    $env:GEMINI_API_KEY = $previousKey
    $payload = $null
    foreach ($setting in $savedLocalSettings.Keys) {
        [Environment]::SetEnvironmentVariable($setting, $savedLocalSettings[$setting], 'Process')
    }
}
exit $childExitCode
