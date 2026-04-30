# Wrapper per `manage.py` nel container web LOCALE (PowerShell).
# Uso: .\scripts\local\manage.ps1 <comando django>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

docker compose -f docker-compose.local.yml --env-file .env.local.docker `
    exec web python manage.py @args
