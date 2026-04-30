# Esegue gli script read-only di prep Postgres dentro il container web (PowerShell).
# Uso: .\scripts\local\smoke.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

function Invoke-WebPython {
    param([Parameter(ValueFromRemainingArguments = $true)] $argv)
    docker compose -f docker-compose.local.yml --env-file .env.local.docker `
        exec -T web python @argv
}

Write-Host "=== check_database_backend.py ===" -ForegroundColor Cyan
Invoke-WebPython scripts/staging/check_database_backend.py
Write-Host ""
Write-Host "=== smoke_database_readiness.py ===" -ForegroundColor Cyan
Invoke-WebPython scripts/staging/smoke_database_readiness.py
