$ErrorActionPreference = "Stop"

Write-Host "Listing all Python processes..." -ForegroundColor Cyan

$procs = Get-CimInstance Win32_Process -Filter "Name like '%python%' OR Name like '%uvicorn%' OR Name like '%node%'" | Select-Object ProcessId, Name, CommandLine

$procs | Format-Table -AutoSize -Wrap

Write-Host "---------------------------------------------------"
Write-Host "Testing Search Filters used in start_ecosystem.ps1:"
Write-Host "---------------------------------------------------"

$capture = $procs | Where-Object { $_.CommandLine -like "*omega_kg.capture_server*" }
if ($capture) { Write-Host "✅ OmegaKG Capture FOUND: $($capture.ProcessId)" -ForegroundColor Green } else { Write-Host "❌ OmegaKG Capture NOT FOUND" -ForegroundColor Red }

$ingest = $procs | Where-Object { $_.CommandLine -like "*uvicorn*ingest_llm_as*" }
if ($ingest) { Write-Host "✅ InGest-LLM FOUND: $($ingest.ProcessId)" -ForegroundColor Green } else { Write-Host "❌ InGest-LLM NOT FOUND" -ForegroundColor Red }

$memos = $procs | Where-Object { $_.CommandLine -like "*memos_mcp*server*" }
if ($memos) { Write-Host "✅ memOS.MCP FOUND: $($memos.ProcessId)" -ForegroundColor Green } else { Write-Host "❌ memOS.MCP NOT FOUND" -ForegroundColor Red }

$cortex = $procs | Where-Object { $_.CommandLine -like "*vite*" }
if ($cortex) { Write-Host "✅ CortexBridge FOUND: $($cortex.ProcessId)" -ForegroundColor Green } else { Write-Host "❌ CortexBridge NOT FOUND" -ForegroundColor Red }
