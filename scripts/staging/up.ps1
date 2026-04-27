# Avvia lo stack staging (Windows PowerShell).
# Uso: .\scripts\staging\up.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

if (-not (Test-Path .env.staging)) {
    Write-Error ".env.staging mancante."
    exit 1
}

docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
Write-Host ""
Write-Host "Stack started. Verifica:"
Write-Host "  docker compose -f docker-compose.staging.yml ps"
Write-Host "  docker compose -f docker-compose.staging.yml logs -f web"
