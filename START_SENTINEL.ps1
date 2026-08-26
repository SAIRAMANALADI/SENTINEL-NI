$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required but the 'docker' command was not found."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running. Start Docker Desktop, then run START_SENTINEL.ps1 again."
}

Write-Host "Starting Sentinel services..." -ForegroundColor Cyan
docker compose up -d --build --wait

if ($LASTEXITCODE -ne 0) {
    throw "Sentinel services did not start successfully. Inspect the output above with: docker compose logs"
}

Write-Host ""
docker compose ps
Write-Host ""
Write-Host "Sentinel is ready:" -ForegroundColor Green
Write-Host "  Primary frontend: http://localhost:3000"
Write-Host "  Streamlit fallback: http://localhost:8501"
Write-Host "  Backend readiness: http://localhost:8000/api/v1/ready"

Start-Process "http://localhost:3000"
