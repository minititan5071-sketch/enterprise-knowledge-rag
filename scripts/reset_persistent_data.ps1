$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Warning "This will delete persistent Docker volumes for PostgreSQL, Qdrant, and uploaded files."
Write-Warning "You will lose registered users, workspaces, document metadata, vectors, and uploaded files."
$Confirmation = Read-Host "Type DELETE to continue"

if ($Confirmation -ne "DELETE") {
    Write-Host "Reset cancelled."
    exit 0
}

docker compose down -v
Write-Host "Persistent Docker data deleted. Run scripts/start_persistent.ps1 to recreate the stack."

