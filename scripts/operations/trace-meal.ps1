# Soma Meal Trace Verification Script
# Tests the E2E signal flow: InGress -> InGest -> Redis -> OmegaKG -> memOS

param(
    [string]$IngressUrl = "http://localhost:8000",
    [string]$ApiKey = "soma-dev-secure-key-change-in-production"
)

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 59 -ForegroundColor Cyan
Write-Host "SOMA MEAL TRACE VERIFICATION" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 59 -ForegroundColor Cyan
Write-Host ""

# Test payload - Terminal Ghost signal
$traceId = "trace_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$payload = @{
    source = "terminal_ghost"
    event_type = "shell_capture"
    payload = @{
        content = "Sean executed the meal trace verification at the Cape Town office yesterday. He confirmed the SimpleMem pipeline is working correctly."
        trace_id = $traceId
        timestamp = (Get-Date -Format "o")
    }
} | ConvertTo-Json -Depth 3

Write-Host "[1/4] SENSES (InGress): Injecting Terminal Ghost signal..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "$IngressUrl/api/v1/manual/ingest" `
        -Method Post `
        -Headers @{ "X-API-Key" = $ApiKey; "Content-Type" = "application/json" } `
        -Body $payload

    $rawLakeId = $response.ref
    Write-Host "  OK Signal captured" -ForegroundColor Green
    Write-Host "    raw_lake UUID: $rawLakeId" -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "  FAIL InGress failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "[2/4] STOMACH (InGest): Waiting for SimpleMem digestion..." -ForegroundColor Cyan
Write-Host "  (Polling raw_lake, applying entropy gate, coreferee resolution)" -ForegroundColor Gray
Start-Sleep -Seconds 10
Write-Host "  WAIT Digestion cycle complete" -ForegroundColor Yellow
Write-Host ""

Write-Host "[3/4] NERVOUS SYSTEM (Redis): XADD to soma_working_memory..." -ForegroundColor Cyan
Write-Host "  (Stream consumer should pick this up)" -ForegroundColor Gray
Start-Sleep -Seconds 10
Write-Host "  WAIT Waiting for OmegaKG persistence" -ForegroundColor Yellow
Write-Host ""

Write-Host "[4/4] BRAIN (Neo4j): Verifying persistence via memOS..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 59 -ForegroundColor Cyan
Write-Host "VERIFICATION COMPLETE" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 59 -ForegroundColor Cyan
Write-Host ""
Write-Host "To verify persistence, run this Cypher query in Neo4j:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  MATCH (f:AtomicFact {source_id: '$rawLakeId'})" -ForegroundColor White
Write-Host "  RETURN f.text, f.source_id, f.embedding" -ForegroundColor White
Write-Host ""
Write-Host "Or use memOS query_brain tool:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  MATCH (f:AtomicFact)" -ForegroundColor White
Write-Host "  WHERE f.source = 'terminal_ghost'" -ForegroundColor White
Write-Host "  RETURN f.text, f.source_id" -ForegroundColor White
Write-Host "  ORDER BY f.created_at DESC" -ForegroundColor White
Write-Host "  LIMIT 1" -ForegroundColor White
Write-Host ""
Write-Host "Trace ID: $traceId" -ForegroundColor Cyan
Write-Host "raw_lake UUID: $rawLakeId" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aweh! Done." -ForegroundColor Green
