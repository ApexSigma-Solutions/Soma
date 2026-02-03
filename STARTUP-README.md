# Soma Ecosystem Startup System

## 🚀 Quick Start

Double-click the **"Soma Ecosystem"** icon on your desktop to launch the entire biomorphic ecosystem with a single action.

## 📁 Files

| File | Purpose |
|------|---------|
| `Start-Soma.bat` | Double-click launcher for Windows |
| `Start-SomaEcosystem.ps1` | Main PowerShell orchestrator with full features |
| `Create-DesktopShortcut.ps1` | Creates desktop shortcut with custom icon |

## ✨ Features

### Pre-Flight Checks
- ✅ PowerShell 7.0+ version validation
- ✅ Python 3.12+ with Poetry
- ✅ Node.js 18+ with npm
- ✅ Docker & Docker Compose
- ✅ Environment variables (SOMA_INGRESS_KEY, SOMA_PG_DSN, etc.)
- ✅ Project directory structure validation

### Infrastructure Management
- ✅ PostgreSQL (port 6000) - Raw lake storage
- ✅ Neo4j (port 7687) - Knowledge graph
- ✅ Redis (port 6380) - Working memory / Nervous system
- ✅ Docker Compose orchestration
- ✅ Health checks with TCP connection testing

### Service Orchestration
Services start in dependency order with health checks:

1. **Senses** (InGress, Port 8000) - Sensory input layer
2. **Stomach** (InGest, Port 8766) - Digestive processing
3. **Brain** (OmegaKG, Port 8765) - Knowledge graph
4. **Bridge** (memOS, Port 8768) - Working memory
5. **Cortex** (Dashboard, Port 6001) - UI/Observer

### Exponential Backoff Retry
Health checks use exponential backoff:
- Initial retry: 2 seconds
- Max retry interval: 30 seconds
- Max retries: 5 (configurable)
- Formula: `backoff = min(previous * 2, 30)`

### Fail-Fast & Fail-Loud
- **Fail-Fast**: Stops immediately on critical service failure
- **Fail-Loud**: Clear error messages with log file locations
- **Verbose Logging**: Full operation logs to `%USERPROFILE%\.soma\logs\`

### Auto-Launch
Automatically opens browser to Cortex Dashboard when all services are healthy.

## 🎯 Usage

### Method 1: Desktop Icon (Recommended)
```powershell
# Run once to create desktop shortcut
.\Create-DesktopShortcut.ps1

# Then double-click "Soma Ecosystem" on your desktop
```

### Method 2: Batch File
```batch
# Double-click Start-Soma.bat
# Or run from command line:
Start-Soma.bat
```

### Method 3: PowerShell (Advanced)
```powershell
# Full control with parameters
.\Start-SomaEcosystem.ps1 -VerboseLogging -MaxRetries 10

# Skip pre-flight checks (not recommended)
.\Start-SomaEcosystem.ps1 -SkipPreflight

# Skip infrastructure startup
.\Start-SomaEcosystem.ps1 -SkipDocker

# Don't open browser
.\Start-SomaEcosystem.ps1 -NoBrowser
```

## 📊 Logging

Logs are stored in: `%USERPROFILE%\.soma\logs\`

Format: `soma-startup-yyyyMMdd-HHmmss.log`

### Log Levels
- **INFO**: General operations
- **SUCCESS**: Successful operations
- **WARNING**: Non-fatal issues
- **ERROR**: Failures
- **CRITICAL**: Fatal errors
- **DEBUG**: Detailed diagnostics (with `-VerboseLogging`)

### Sample Log Output
```
[2026-02-01 14:32:15.123] [INFO] [SYSTEM] Soma Ecosystem Startup v2.0.0
[2026-02-01 14:32:15.456] [SUCCESS] [PREFLIGHT] PowerShell 7.4.0
[2026-02-01 14:32:16.789] [SUCCESS] [PREFLIGHT] Python found | Version=3.12.1, Path=C:\Python312\python.exe
[2026-02-01 14:32:18.012] [SUCCESS] [INFRA] PostgreSQL is available on port 6000
[2026-02-01 14:32:20.345] [SUCCESS] [Senses] ✓ Senses is healthy | StatusCode=200, Retry=0
[2026-02-01 14:32:23.678] [SUCCESS] [LAUNCH] ✓ Browser launched successfully
```

## ⚙️ Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-SkipPreflight` | Switch | False | Skip dependency checks |
| `-SkipDocker` | Switch | False | Skip infrastructure startup |
| `-VerboseLogging` | Switch | False | Enable debug logging |
| `-MaxRetries` | Int | 5 | Health check retry attempts |
| `-InitialBackoffSeconds` | Int | 2 | Initial retry delay |
| `-LogPath` | String | `~\.soma\logs` | Log directory |
| `-NoBrowser` | Switch | False | Don't auto-open browser |
| `-DebugMode` | Switch | False | Enable debug mode |

## 🔧 Troubleshooting

### "PowerShell not found"
Install PowerShell 7: https://github.com/PowerShell/PowerShell/releases

### "Docker not running"
Start Docker Desktop before running the script.

### "Service failed to start"
Check logs: `%USERPROFILE%\.soma\logs\`

### "Port already in use"
Check for conflicting services:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOMA ECOSYSTEM v2.0                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Senses     │───▶│   Stomach    │───▶│    Brain     │  │
│  │  (InGress)   │    │   (InGest)   │    │  (OmegaKG)   │  │
│  │   :8000      │    │   :8766      │    │   :8765      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                         │                                   │
│                         ▼                                   │
│                  ┌──────────────┐                          │
│                  │    Bridge    │                          │
│                  │   (memOS)    │                          │
│                  │   :8768      │                          │
│                  └──────────────┘                          │
│                         │                                   │
│                         ▼                                   │
│                  ┌──────────────┐                          │
│                  │    Cortex    │                          │
│                  │  (Dashboard) │                          │
│                  │   :6001      │                          │
│                  └──────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📜 Compliance

- **ApexSigma Naming**: Biological terminology (Senses/Stomach/Brain)
- **MAR Protocol v2.0**: Forensic logging, structured output
- **Mirmir Constraints**: EVT-50N42 password validation

## 🎉 Success Criteria

When the ecosystem is fully operational, you'll see:

```
✓ SOMA ECOSYSTEM IS OPERATIONAL
  All services are healthy and ready

Service Status:
  Senses ✓ HEALTHY
  Stomach ✓ HEALTHY
  Brain ✓ HEALTHY
  Bridge ✓ HEALTHY
  Cortex ✓ HEALTHY

🧠 Cortex Dashboard: http://localhost:6001
```

And your browser will automatically open to the Cortex Control Bridge.
