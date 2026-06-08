$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.persistent.example" ".env"
    Write-Host "Created .env from .env.persistent.example"
} else {
    Write-Host ".env already exists; leaving it unchanged."
    Write-Host "To refresh persistent defaults, compare it with .env.persistent.example."
}

Write-Host "Starting persistent local enterprise stack..."
Write-Host "Backend containers will reach LM Studio at http://host.docker.internal:1234/v1"
docker compose up --build

