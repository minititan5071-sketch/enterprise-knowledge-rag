$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "Stopping persistent local enterprise stack without deleting volumes..."
docker compose down

Write-Host "Stopped. PostgreSQL, Qdrant, and uploaded file volumes are preserved."

