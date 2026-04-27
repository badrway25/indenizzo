# Wrapper per `manage.py` nel container web (Windows PowerShell).
# Uso: .\scripts\staging\manage.ps1 <comando>
# Es : .\scripts\staging\manage.ps1 migrate
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

docker compose -f docker-compose.staging.yml --env-file .env.staging `
    exec web python manage.py @args
