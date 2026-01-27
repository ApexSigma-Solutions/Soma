#!/usr/bin/env pwsh
# Commit and push PR #85 review comment fixes

Write-Host "📝 Committing PR #85 review fixes..." -ForegroundColor Green

git add -A

git commit -m "fix: address GitHub PR #85 review comments - code quality and security improvements

- Fix undefined mock_datetime variable in test_capture_server.py (test was trying to use mock_datetime before it was captured)
- Fix test duration logic in smoke_test_core_stack.py to prevent exceeding specified monitoring duration
- Improve pydantic-settings compatibility using *args and **kwargs for version compatibility
- Refactor create_relationships_based_on_similarity to use single query (prevents N+1 query pattern)
- Remove hardcoded test container password from conftest.py (let Testcontainers handle auth)
- Use global settings object instead of instantiating Settings repeatedly in percolation.py
- Clean up temporary and debug files (.omegakg_temp, .ignore, debug_test.py, etc.)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Commit successful" -ForegroundColor Green
    
    Write-Host "🚀 Pushing to origin/onboard-serena..." -ForegroundColor Green
    git push origin onboard-serena
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Push successful! PR #85 is ready for merge" -ForegroundColor Green
    } else {
        Write-Host "❌ Push failed" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Commit failed" -ForegroundColor Red
}
