[CmdletBinding()]
param(
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\compose.fullstack.yaml"),
    [string]$ProjectName = "backend",
    [string]$OutputDirectory
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

$ComposeFile = [System.IO.Path]::GetFullPath($ComposeFile)
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    throw "Compose file not found: $ComposeFile"
}

if (-not $OutputDirectory) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDirectory = Join-Path (Split-Path $ComposeFile -Parent) "backups\$timestamp"
}

$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$databaseBackup = Join-Path $OutputDirectory "postgres.dump"
$minioBackup = Join-Path $OutputDirectory "minio-data.tar.gz"
$manifestPath = Join-Path $OutputDirectory "manifest.json"

foreach ($path in @($databaseBackup, $minioBackup, $manifestPath)) {
    if (Test-Path -LiteralPath $path) {
        throw "Refusing to overwrite an existing backup file: $path"
    }
}

Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "up", "-d", "postgres", "minio")
$databaseContainer = Get-ComposeContainerId -Service "postgres"
$minioVolume = "${ProjectName}_minio-data"

try {
    Invoke-Docker -DockerArguments @(
        "exec", $databaseContainer, "sh", "-lc",
        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file=/tmp/darafin-share.dump'
    )
    Invoke-Docker -DockerArguments @("cp", "${databaseContainer}:${temporaryDump}", $databaseBackup)
}
finally {
    & docker exec $databaseContainer rm -f $temporaryDump 2>$null | Out-Null
}

# MinIO stores object metadata next to the objects. Stop it briefly for a consistent archive.
Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "stop", "minio")
try {
    Invoke-Docker -DockerArguments @(
        "run", "--rm",
        "--mount", "type=volume,source=$minioVolume,target=/data,readonly",
        "--mount", "type=bind,source=$OutputDirectory,target=/backup",
        $helperImage,
        "sh", "-lc", "tar -czf /backup/minio-data.tar.gz -C /data ."
    )
}
finally {
    Invoke-Docker -DockerArguments @("compose", "-f", $ComposeFile, "up", "-d", "minio")
}

$files = foreach ($file in @($databaseBackup, $minioBackup)) {
    $item = Get-Item -LiteralPath $file
    [ordered]@{
        name = $item.Name
        bytes = $item.Length
        sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$manifest = [ordered]@{
    formatVersion = 1
    createdAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    projectName = $ProjectName
    includes = @("postgres", "minio")
    excludes = @("redis")
    files = $files
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8NoBOM
Write-Host "Backup created at: $OutputDirectory"
Write-Warning "The backup may contain sensitive data. Keep it out of Git and transfer it only through an encrypted private channel."
