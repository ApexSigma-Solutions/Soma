# Unified Launcher for OmegaKG
# Launches all services in a single Windows Terminal window with named tabs.

$ProjectRoot = "D:\projects\OmegaKG"
$StableRoot = "$ProjectRoot\Omega_KG_stable"
$MemosRoot = "$ProjectRoot\memos.MCP"
$FrontendRoot = "$ProjectRoot\CortexBridge"
$IngestRoot = "$ProjectRoot\InGest-LLM.as"

Write-Host "Preparing to launch OmegaKG Ecosystem..." -ForegroundColor Cyan

# 1. Kill Check
Stop-Process -Name "python", "node" -Force -ErrorAction SilentlyContinue

# 2. Construct WT Command
# We use `;` to separate commands (tabs) in wt arguments.
# split-pane looks cool but tabs are often more readable for logs. Let's use tabs.

# Construct the arguments as a single string, using a placeholder for the semicolon
# Windows Terminal accepts ; to separate tabs, but PowerShell eats it.
# We will use Start-Process with a carefully constructed argument list.

$ArgsList = "-w", "0", "new-tab", "--title", "Monitor", "-p", "PowerShell", "-d", "$ProjectRoot", "powershell", "-NoExit", "-File", "scripts\operations\monitor-dashboard.ps1"

$ArgsList += ";", "new-tab", "--title", "Backend", "-p", "PowerShell", "-d", "$StableRoot", "cmd", "/k", "poetry run python -m omega_kg.capture_server"

$ArgsList += ";", "new-tab", "--title", "memOS", "-p", "PowerShell", "-d", "$MemosRoot", "cmd", "/k", "poetry run python src/memos_mcp/server.py --sse"

$ArgsList += ";", "new-tab", "--title", "Frontend", "-p", "PowerShell", "-d", "$FrontendRoot", "cmd", "/k", "npm run dev -- --port 6001"

$ArgsList += ";", "new-tab", "--title", "InGest", "-p", "PowerShell", "-d", "$IngestRoot", "cmd", "/k", "set PYTHONPATH=%cd%\src && poetry run uvicorn ingest_llm_as.main:app --host 0.0.0.0 --port 8766 --reload"

$ArgsList += ";", "new-tab", "--title", "GraphParser", "-p", "PowerShell", "-d", "$IngestRoot", "cmd", "/k", "set PYTHONPATH=%cd%\src && poetry run uvicorn ingest_llm_as.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Launching Windows Terminal..."
Start-Process "wt" -ArgumentList $ArgsList

