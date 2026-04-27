# Build dell'immagine staging (Windows PowerShell).
# Uso: .\scripts\staging\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

if (-not (Test-Path .env.staging)) {
    Write-Error ".env.staging mancante. Copia .env.staging.example e popola."
    exit 1
}

docker compose -f docker-compose.staging.yml --env-file .env.staging build $args
Write-Host "Build OK. Run .\scripts\staging\up.ps1 per avviare."
