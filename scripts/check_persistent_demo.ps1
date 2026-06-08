$ErrorActionPreference = "Continue"

$ExpectedModel = "qwen/qwen3.6-27b"

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url
    )

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
        Write-Host "[OK] $Name reachable: $Url (HTTP $($Response.StatusCode))"
        return $Response
    } catch {
        Write-Host "[FAIL] $Name not reachable: $Url"
        Write-Host "       $($_.Exception.Message)"
        return $null
    }
}

Write-Host "Checking persistent local enterprise demo dependencies..."
Write-Host ""

$Backend = Test-HttpEndpoint -Name "FastAPI backend" -Url "http://localhost:8000/health"
if (-not $Backend) {
    Write-Host "Troubleshooting: start the stack with scripts/start_persistent.ps1 and wait for backend health checks."
}

$Qdrant = Test-HttpEndpoint -Name "Qdrant" -Url "http://localhost:6333"
if (-not $Qdrant) {
    Write-Host "Troubleshooting: ensure docker compose has the qdrant service running and port 6333 is not blocked."
}

$Models = Test-HttpEndpoint -Name "LM Studio models endpoint" -Url "http://localhost:1234/v1/models"
if ($Models) {
    try {
        $Json = $Models.Content | ConvertFrom-Json
        $ModelIds = @($Json.data | ForEach-Object { $_.id })
        if ($ModelIds -contains $ExpectedModel) {
            Write-Host "[OK] LM Studio model available: $ExpectedModel"
        } else {
            Write-Host "[FAIL] Expected LM Studio model not found: $ExpectedModel"
            Write-Host "       Available models:"
            if ($ModelIds.Count -gt 0) {
                $ModelIds | ForEach-Object { Write-Host "       - $_" }
            } else {
                Write-Host "       No models returned by LM Studio."
            }
            Write-Host "Troubleshooting: load the Qwen model in LM Studio and verify the exact model id."
        }
    } catch {
        Write-Host "[FAIL] Could not parse LM Studio /v1/models response."
        Write-Host "       $($_.Exception.Message)"
    }
} else {
    Write-Host "Troubleshooting: in LM Studio, start the Local Server on port 1234."
}

Write-Host ""
Write-Host "Container-to-host LM Studio URL for Docker services: http://host.docker.internal:1234/v1"
Write-Host "Host-side LM Studio check URL: http://localhost:1234/v1/models"

