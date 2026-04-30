# Tail dei log dei servizi locali (PowerShell).
# Uso: .\scripts\local\logs.ps1
#       .\scripts\local\logs.ps1 web
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

docker compose -f docker-compose.local.yml --env-file .env.local.docker logs -f @args
