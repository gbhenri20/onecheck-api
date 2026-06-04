# Inicia a API OneCheck localmente
Set-Location $PSScriptRoot
if (-not (Test-Path "onecheck.db")) {
    Write-Host "Executando seed inicial..."
    py -3 scripts\seed.py
}
Write-Host "API em http://localhost:8000"
Write-Host "Docs:  http://localhost:8000/docs"
py -3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
