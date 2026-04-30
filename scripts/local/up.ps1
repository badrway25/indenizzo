# Avvia lo stack docker LOCALE (Windows PowerShell).
# Uso: .\scripts\local\up.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

if (-not (Test-Path .env.local.docker)) {
    Write-Error ".env.local.docker mancante. Copialo da .env.local.docker.example:`n  Copy-Item .env.local.docker.example .env.local.docker"
    exit 1
}

docker compose -f docker-compose.local.yml --env-file .env.local.docker up --build @args
