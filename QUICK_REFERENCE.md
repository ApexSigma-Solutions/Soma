# Soma Ecosystem - Quick Reference Card

## 🚀 Daily Operations

```powershell
# Start everything (easiest way)
Double-click "Start Soma Ecosystem" on desktop

# Start from command line
.\start_ecosystem.ps1

# Start with watchdog monitoring
.\start_ecosystem.ps1 -Persistent

# Debug mode (see console windows)
.\start_ecosystem.ps1 -ShowConsole -LogLevel Debug
```

## 🧪 Testing

```powershell
# Run full test suite
.\test_ecosystem.ps1

# Run meal trace (E2E test)
.\scripts\operations\trace-meal.ps1

# Check service health manually
Invoke-WebRequest http://localhost:8000/health  # InGress
Invoke-WebRequest http://localhost:8766/health  # InGest
Invoke-WebRequest http://localhost:8765/health  # OmegaKG
Invoke-WebRequest http://localhost:8768/health  # memOS
```

## 🌐 Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Cortex Dashboard** | http://localhost:5173 | Main UI |
| InGress API | http://localhost:8000/docs | Sensory layer |
| InGest API | http://localhost:8766/docs | Metabolism |
| OmegaKG API | http://localhost:8765/docs | Knowledge graph |
| memOS API | http://localhost:8768/docs | MCP tools |
| Neo4j Browser | http://localhost:7474 | Graph database |

## 📊 Monitoring

```powershell
# View live logs
Get-Content logs\startup_*.log -Wait

# Check service status
Get-Process | Where-Object {$_.Path -like "*poetry*" -or $_.Path -like "*npm*"}

# View specific service log
Get-Content logs\InGress.log -Tail 50
Get-Content logs\InGress.error.log -Tail 50
```

## 🔧 Maintenance

```powershell
# Database migrations
python scripts/database/migrate_all.py upgrade

# Contract validation
python contracts/validate_contracts.py

# Update dependencies (per service)
cd InGress && poetry update
cd InGest && poetry update
cd OmegaKG && poetry update
cd memOS && poetry update
cd Cortex && npm update
```

## 🛑 Stop Services

```powershell
# Graceful stop (from startup window)
Press Ctrl+C

# Force stop all
Get-Process | Where-Object {$_.Path -like "*poetry*" -or $_.Path -like "*npm*"} | Stop-Process

# Stop Docker
docker compose down
```

## 🔄 Restart Single Service

```powershell
# Find and kill process
Get-Process | Where-Object {$_.Path -like "*poetry*"} | Where-Object {$_.CommandLine -like "*InGress*"} | Stop-Process

# Restart manually
cd InGress
poetry run python -m soma_ingress.main
```

## 🐛 Troubleshooting

```powershell
# Check if ports are in use
netstat -ano | findstr "8000 8766 8765 8768 5173 6000 7687 6380"

# Verify Docker containers
docker ps

# Check Poetry environments
poetry env info  # Run in each service directory

# Test database connectivity
psql -h localhost -p 6000 -U omega_user -d omega_kg_stable
```

## 📝 Log Files Location

All logs in: `D:\projects\Soma\logs\`

- `startup_YYYYMMDD_HHMMSS.log` - Orchestrator
- `<service>.log` - Service stdout
- `<service>.error.log` - Service stderr
- `test_results_YYYYMMDD_HHMMSS.json` - Test results

## 🎯 Common Issues

| Problem | Solution |
|---------|----------|
| Port already in use | `netstat -ano \| findstr <port>` then kill process |
| Poetry not found | Install: `pip install poetry` |
| Docker not running | Start Docker Desktop |
| Health checks failing | Check logs in `logs/` directory |
| Neo4j connection failed | OmegaKG runs in mock mode (graceful) |

## 🔐 Environment Files

- `.env` (root) - Python services configuration
- `Cortex/.env` - Dashboard API endpoints
- Check `.env.example` for template

## 🎨 Desktop Shortcut

```powershell
# Create shortcut (one-time)
.\create_desktop_shortcut.ps1

# Create with persistent mode
.\create_desktop_shortcut.ps1 -Persistent

# Create with debug mode
.\create_desktop_shortcut.ps1 -ShowConsole
```

## 📞 Getting Help

1. Check `STARTUP_GUIDE.md` for detailed docs
2. Check `AGENTS.md` for architecture
3. Check `REFACTORING_SUMMARY.md` for changes
4. Check service logs in `logs/` directory
5. Run test suite: `.\test_ecosystem.ps1`

---

**Version**: 2.0 | **Platform**: Windows 11 | **Updated**: 2026-01-30
