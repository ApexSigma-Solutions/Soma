# Quick test - Start InGest-LLM on port 8000 instead of 8766
$ProjectRoot = "D:\projects\OmegaKG\InGest-LLM.as"

Write-Host "Starting InGest-LLM on port 8000..." -ForegroundColor Cyan

Push-Location $ProjectRoot

# Run bootstrap first
Write-Host "Running bootstrap..." -ForegroundColor Yellow
poetry run python bootstrap.py

# Start uvicorn on port 8000
Write-Host "`nStarting Uvicorn on port 8000..." -ForegroundColor Cyan
poetry run uvicorn ingest_llm_as.main:app --port 8000 --reload

Pop-Location
