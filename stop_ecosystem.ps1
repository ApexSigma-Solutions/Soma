param([switch]$Full,[switch]$AppsOnly)
function Write-Log($m,$l='INFO') {
  $c = 'Cyan'
  if($l -eq 'WARN'){$c='Yellow'}
  elseif($l -eq 'ERROR'){$c='Red'}
  elseif($l -eq 'SUCCESS'){$c='Green'}
  Write-Host ('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $m) -ForegroundColor $c
}
function Terminate-App($name,$pat,$lbl) {
  $procs = Get-CimInstance Win32_Process -Filter ("Name like '%" + $name + "%'")
  if ($procs) {
    foreach ($p in $procs) {
      if ($p.CommandLine -like ('*' + $pat + '*')) {
        Write-Log ('Terminating ' + $lbl + ' (PID: ' + $p.ProcessId + ')') 'WARN'
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
      }
    }
  }
}

Write-Log '========================================'
Write-Log 'OmegaKG Ecosystem Shutdown'
Write-Log '========================================'

Write-Log 'Stopping Application Services...'
Terminate-App 'python' 'memos_mcp' 'memOS.MCP'
Terminate-App 'python' 'omega_kg.capture_server' 'Capture Server'
Terminate-App 'python' 'omega_kg.workers.embedding_worker' 'Embedding Worker'
Terminate-App 'python' 'omega_kg.workers.vector_index_worker' 'Vector Index Worker'
Terminate-App 'python' 'ingest_llm_as' 'InGest API'
Terminate-App 'uvicorn' 'ingest_llm_as' 'InGest Uvicorn'
Terminate-App 'cloudflared' 'tunnel' 'Cloudflared Tunnel'
Terminate-App 'python' 'log_watchdog.py' 'Log Watchdog'
# Terminate-App 'node' 'vite' 'CortexBridge (Vite)'
# Terminate-App 'node' 'cortex' 'CortexBridge'

$StopDB = $false
if ($AppsOnly) {
  Write-Log 'Skipping DB Shutdown (-AppsOnly)'
} elseif ($Full) {
  $StopDB = $true
} else {
  Write-Host 'Shutdown databases? (y/n): ' -NoNewline
  $res = Read-Host
  if ($res -match 'y') { $StopDB = $true }
}

if ($StopDB) {
  Write-Log 'Stopping Database Containers...' 'WARN'
  $d = Get-Command docker -ErrorAction SilentlyContinue
  if ($d) {
    $conts = 'apexsigma.redis', 'apexsigma.postgres', 'apexsigma.neo4j', 'memos-redis'
    foreach ($c in $conts) {
      $id = docker ps -q -f ("name=" + $c)
      if ($id) {
        Write-Log ('  Stopping ' + $c + '...')
        docker stop $c | Out-Null
        Write-Log ('  ✓ ' + $c + ' stopped') 'SUCCESS'
      }
    }
  } else {
    Write-Log 'Docker not found' 'ERROR'
  }
} else {
  Write-Log 'Databases left running.'
}

Write-Log ''
Write-Log 'Shutdown Complete.' 'SUCCESS'
Write-Log '========================================'
