param([switch]$Inside, [switch]$Browser)
$ErrorActionPreference = 'Stop'
$testRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $testRoot
if (-not $Inside) {
    New-Item -ItemType Directory -Path '.cache' -Force | Out-Null
    $configuration = @{
        firestore = @{rules=(Join-Path $testRoot 'firestore.rules'); indexes=(Join-Path $testRoot 'firestore.indexes.json')}
        emulators = @{
            firestore=@{host='127.0.0.1';port=18081;websocketPort=19150}
            auth=@{host='127.0.0.1';port=19099}; hub=@{host='127.0.0.1';port=14400}
            logging=@{host='127.0.0.1';port=14401};ui=@{enabled=$false};singleProjectMode=$true
        }
    }
    [IO.File]::WriteAllText((Join-Path $testRoot '.cache/firebase-isolated-integration.json'), ($configuration | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    $childCommand = 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test-local.ps1 -Inside'
    if ($Browser) { $childCommand += ' -Browser' }
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/firebase.ps1 emulators:exec --config .cache/firebase-isolated-integration.json --only auth,firestore --project demo-aml-insight $childCommand
    exit $LASTEXITCODE
}
if ($env:FIRESTORE_EMULATOR_HOST -ne '127.0.0.1:18081' -or $env:FIREBASE_AUTH_EMULATOR_HOST -ne '127.0.0.1:19099') { throw 'Wrong isolated emulator endpoints.' }
$env:APP_MODE='local'
$env:GOOGLE_CLOUD_PROJECT='demo-aml-insight'
$env:LIVE_AI_ENABLED='false'
$env:LOCAL_GEMINI_ENABLED='false'
$env:LOCAL_GEMINI_FREE_VERIFIED='false'
$env:CLOUD_TASKS_ENABLED='false'
$env:CREDITS_VERIFIED='false'
$env:GEMINI_API_KEY=$null
$env:AGENT_PROFILES_JSON=''
$env:OPERATOR_UIDS='operator-demo'
$env:ADMIN_UIDS='operator-demo'
if (-not $Browser) {
    & .venv/Scripts/python.exe -m pytest tests/test_integration.py tests/test_bulk_integration.py -q --junitxml=.cache/integration-results.xml
    exit $LASTEXITCODE
}
& .venv/Scripts/python.exe -m backend.seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .venv/Scripts/python.exe -m backend.bulk_dataset
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& .venv/Scripts/python.exe -m backend.bulk_jobs --import-local
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:GENESIS_BROWSER_BASE_URL='http://127.0.0.1:15173'
$env:GENESIS_API_TARGET='http://127.0.0.1:18080'
$testPython=(Resolve-Path '.venv/Scripts/python.exe').Path
$api=Start-Process -FilePath $testPython -ArgumentList '-m','uvicorn','backend.api:app','--host','127.0.0.1','--port','18080' -WindowStyle Hidden -PassThru -RedirectStandardOutput '.cache/isolated-browser-api.log' -RedirectStandardError '.cache/isolated-browser-api-error.log'
$sourcePreview=$null
try {
    $ready=$false
    for ($attempt=0;$attempt -lt 60;$attempt++) {
        if ($api.HasExited) { throw 'Isolated API exited.' }
        try { $null=Invoke-RestMethod 'http://127.0.0.1:18080/api/health' -TimeoutSec 1; $ready=$true;break }
        catch { Start-Sleep -Milliseconds 200 }
    }
    if (-not $ready) { throw 'Isolated API not ready.' }
    $testNode=(Get-Command node.exe).Source
    $sourcePreview=Start-Process -FilePath $testNode -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15173','--strictPort' -WindowStyle Hidden -PassThru -RedirectStandardOutput '.cache/isolated-browser-vite.log' -RedirectStandardError '.cache/isolated-browser-vite-error.log'
    $sourceReady=$false
    for($attempt=0;$attempt -lt 60;$attempt++) {
        if($sourcePreview.HasExited) { throw 'Source preview exited.' }
        try { $null=Invoke-RestMethod 'http://127.0.0.1:15173' -TimeoutSec 1; $sourceReady=$true;break }
        catch { Start-Sleep -Milliseconds 200 }
    }
    if(-not $sourceReady) { throw 'Source preview not ready.' }
    & npm.cmd run test:browser
    $result=$LASTEXITCODE
} finally { if ($sourcePreview -and -not $sourcePreview.HasExited) { Stop-Process -Id $sourcePreview.Id }; if (-not $api.HasExited) { Stop-Process -Id $api.Id; $api.WaitForExit() } }
exit $result
