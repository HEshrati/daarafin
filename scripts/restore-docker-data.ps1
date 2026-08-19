[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BackupDirectory,
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\compose.fullstack.yaml"),
    [string]$ProjectName = "backend",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$helperImage = "node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32"
$temporaryDump = "/tmp/darafin-share.dump"

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$DockerArguments)

    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($DockerArguments -join ' ')"
    }
}

function Get-ComposeContainerId {
    param([Parameter(Mandatory)][string]$Service)

    $containerId = (& docker compose -f $ComposeFile ps -q $Service | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $containerId) {
        throw "Could not resolve the running container for service '$Service'."
    }
    return $containerId
}

if (-not $Force) {
    throw "Restore replaces the current PostgreSQL and MinIO data. Re-run with -Force after verifying the target environment."
}

$ComposeFile = [System.IO.Path]::GetFullPath($ComposeFile)
$BackupDirectory = [System.IO.Path]::GetFullPath($BackupDirectory)
$manifestPath = Join-Path $BackupDirectory "manifest.json"

if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    throw "Compose file not found: $ComposeFile"
}
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Backup manifest not found: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.formatVersion -ne 1) {
    throw "Unsupported backup format version: $($manifest.formatVersion)"
}

foreach ($entry in $manifest.files) {
    $path = Join-Path $BackupDirectory $entry.name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Backup file is missing: $path"
    }
    $actualHash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $entry.sha256) {
        throw "Checksum mismatch for backup file: $($entry.name)"
    }
}

$databaseBackup = Join-Path $BackupDirectory "postgres.dump"
$minioBackup = Join-Path $BackupDirectory "minio-data.tar.gz"
$minioVolume = "${ProjectName}_minio-data"

Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "up", "-d", "postgres", "minio")
Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "stop", "web", "worker", "beat", "frontend", "minio")
$databaseContainer = Get-ComposeContainerId -Service "postgres"

try {
    Invoke-Docker -DockerArguments @("cp", $databaseBackup, "${databaseContainer}:${temporaryDump}")
    Invoke-Docker -DockerArguments @(
        "exec", $databaseContainer, "sh", "-lc",
        'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --exit-on-error /tmp/darafin-share.dump'
    )
}
finally {
    & docker exec $databaseContainer rm -f $temporaryDump 2>$null | Out-Null
}

Invoke-Docker -DockerArguments @(
    "run", "--rm",
    "--mount", "type=volume,source=$minioVolume,target=/data",
    "--mount", "type=bind,source=$BackupDirectory,target=/backup,readonly",
    $helperImage,
    "sh", "-lc",
    "find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf /backup/minio-data.tar.gz -C /data"
)

Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "up", "-d")
Write-Host "Restore completed from: $BackupDirectory"
