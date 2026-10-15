# Installs free portable tooling only. Run from Genesis; never signs in or creates resources.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolRoot = Join-Path $projectRoot '.tools'
$downloadRoot = Join-Path $projectRoot '.cache/downloads'
New-Item -ItemType Directory -Force -Path $toolRoot, $downloadRoot | Out-Null

function Get-VerifiedArchive([string] $Url, [string] $File, [string] $ExpectedHash) {
    if (-not (Test-Path -LiteralPath $File)) {
        Write-Output "Downloading: $([IO.Path]::GetFileName($File))"
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $File
    }
    $actualHash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash
    if ($actualHash -ne $ExpectedHash) { throw "SHA256 mismatch for $File; do not execute it." }
}

$cloudUrl = 'https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-589.0.0-windows-x86_64-bundled-python.zip'
$cloudHash = 'b9c2f4f296154f55e8a31a6979106573bc1ad8691041d4a32ea90c1834fdf995'
$cloudArchive = Join-Path $downloadRoot 'google-cloud-sdk-589.0.0.zip'
$cloudCommand = Join-Path $toolRoot 'google-cloud-sdk/bin/gcloud.cmd'
if (-not (Test-Path -LiteralPath $cloudCommand)) {
    Get-VerifiedArchive $cloudUrl $cloudArchive $cloudHash
    Write-Output 'Extracting Google Cloud CLI into Genesis/.tools...'
    Expand-Archive -LiteralPath $cloudArchive -DestinationPath $toolRoot
}

$javaRoot = Join-Path $toolRoot 'java'
$javaHomes = @(Get-ChildItem -LiteralPath $javaRoot -Directory -ErrorAction SilentlyContinue | Where-Object {
    Test-Path -LiteralPath (Join-Path $_.FullName 'bin/java.exe')
})
$javaMetadataPath = Join-Path $toolRoot 'java-download.json'
if ($javaHomes.Count -eq 0) {
    $javaAssets = Invoke-RestMethod -Uri 'https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jre&os=windows&vendor=eclipse'
    $javaAsset = @($javaAssets)[0]
    if (-not $javaAsset.binary.package.link -or -not $javaAsset.binary.package.checksum) { throw 'Missing Java download metadata.' }
    $javaArchive = Join-Path $downloadRoot $javaAsset.binary.package.name
    Get-VerifiedArchive $javaAsset.binary.package.link $javaArchive $javaAsset.binary.package.checksum
    New-Item -ItemType Directory -Force -Path $javaRoot | Out-Null
    Write-Output 'Extracting Eclipse Temurin Java 21 runtime into Genesis/.tools...'
    Expand-Archive -LiteralPath $javaArchive -DestinationPath $javaRoot
    @{version=$javaAsset.version.semver;url=$javaAsset.binary.package.link;sha256=$javaAsset.binary.package.checksum} |
        ConvertTo-Json | Set-Content -LiteralPath $javaMetadataPath -Encoding UTF8
}
Write-Output 'Portable tooling extracted. Run npm run doctor to verify; no cloud authentication performed.'
