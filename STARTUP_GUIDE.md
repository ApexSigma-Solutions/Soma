# Soma Ecosystem Startup Guide

**Version:** 2.0 - Robust Windows 11 Edition  
**Updated:** 2026-01-30

## Quick Start

### Option 1: Desktop Shortcut (Recommended)

1. **Create the shortcut** (one-time setup):
   ```powershell
   .\create_desktop_shortcut.ps1
   ```

2. **Double-click** "Start Soma Ecosystem" on your desktop

3. **Access Cortex Dashboard**: http://localhost:5173

### Option 2: Command Line

```powershell
# Standard startup
.\start_ecosystem.ps1

# With persistent monitoring
.\start_ecosystem.ps1 -Persistent

# Debug mode with visible consoles
.\start_ecosystem.ps1 -ShowConsole -LogLevel Debug

# Skip migrations and contracts
.\start_ecosystem.ps1 -SkipMigrations -SkipContracts
```

---

## What's New in v2.0

### ✅ Robust Error Handling
- **Exponential backoff retry logic** (not fixed intervals)
- **Configurable retry attempts** per service type
- **Jitter added** to prevent thundering herd
- **Graceful degradation** - one service failure doesn't crash others

### ✅ Decoupled Service Management
- **Independent startup** - services start even if others fail
- **Dependency tracking** - services wait for their dependencies
- **Priority-based ordering** - Docker → Python → Node
- **Health status tracking** - individual service health monitoring

### ✅ Comprehensive Logging
- **Verbose logging** with configurable levels (Debug, Info, Warning, Error)
- **Timestamped logs** in `logs/` directory
- **Per-service logs** - separate files for each service
- **Color-coded console** output for readability

### ✅ Automatic Recovery (Persistent Mode)
- **Watchdog monitoring** - checks health every 30 seconds
- **Automatic restart** on service crashes (up to 3 attempts)
- **Recovery tracking** - prevents infinite restart loops
- **Health state transitions** - Healthy → Unhealthy → Failed

### ✅ Windows 11 Optimized
- **PowerShell 7 syntax** for best performance
- **Proper execution policies** for security
- **UTF-8 encoding** for international support
- **Desktop shortcut** for easy access

---

## Architecture

### Service Dependency Tree

```
Docker Infrastructure (Priority 1)
├── Postgres:6000
├── Neo4j:7687
└── Redis:6380
    │
    ├─→ InGress:8000 (Priority 2)
    │   └─→ InGest:8766 (Priority 3)
    │
    ├─→ OmegaKG:8765 (Priority 3)
    │   └─→ memOS:8768 (Priority 4)
    │
    └─→ Cortex:5173 (Priority 5)
        └─→ Requires: InGress, InGest, OmegaKG, memOS
```

### Health Check Strategy

1. **Docker Services**: TCP port checks + pg_isready
2. **Python Services**: HTTP `/health` endpoints with JSON response
3. **Cortex**: HTTP response on port 5173

### Retry Configuration

| Service | Max Retries | Base Delay | Max Delay |
|---------|-------------|------------|-----------|
| Docker Services | 5 | 2s | 60s |
| Python Services | 10 | 3s | 60s |
| Cortex | 8 | 2s | 60s |

**Formula**: Delay = min(BaseDelay × 2^Attempt + Jitter, MaxDelay)

---

## Service Details

### Docker Infrastructure

**PostgreSQL**
- Port: 6000 (host-mapped from 5432)
- Health: `pg_isready -h localhost -p 6000`
- Volume: `apexsigma.postgres.data`

**Neo4j**
- Bolt: 7687 (host-mapped)
- Browser: 7474 (host-mapped)
- Volume: `apexsigma.neo4j.data`

**Redis**
- Port: 6380 (host-mapped from 6379)
- Volume: `apexsigma.redis.data`

### Python Services

**InGress (Senses)**
- Port: 8000
- Entry: `soma_ingress.main`
- Health: `/health`
- Docs: http://localhost:8000/docs
- Depends: Postgres, Redis

**InGest (Stomach)**
- Port: 8766
- Entry: `ingest_llm_as.main`
- Health: `/health`
- Docs: http://localhost:8766/docs
- Depends: Postgres, Redis, InGress

**OmegaKG (Brain)**
- Port: 8765
- Entry: `omega_kg.main`
- Health: `/health`
- Docs: http://localhost:8765/docs
- Depends: Postgres, Neo4j, Redis
- **Special**: Gracefully degrades to mock mode if Neo4j unavailable

**memOS (Hands)**
- Port: 8768
- Entry: `memos_mcp.server`
- Health: `/health`
- Docs: http://localhost:8768/docs
- Depends: Postgres, OmegaKG

### Cortex Dashboard

- Port: 5173
- Tech: React 19 + Vite + TypeScript
- Health: HTTP 200 on root
- Depends: All Python services

**Telemetry Integration:**
- Health polling: Every 10 seconds
- SSE streams: InGress (`/api/v1/telemetry/stream`), memOS (`/pulse/stream`)
- API clients: Auto-retry with exponential backoff (3 attempts)

---

## Testing

### Manual Testing

1. **Start ecosystem**:
   ```powershell
   .\start_ecosystem.ps1
   ```

2. **Run test suite**:
   ```powershell
   .\test_ecosystem.ps1
   ```

3. **Run meal trace**:
   ```powershell
   .\scripts\operations\trace-meal.ps1
   ```

### Automated Testing

The `test_ecosystem.ps1` script validates:
- ✅ Docker infrastructure connectivity
- ✅ Python service health endpoints
- ✅ Cortex dashboard accessibility
- ✅ Service integration (telemetry streams)
- ✅ End-to-end flow (meal trace)

**Success criteria**: All services healthy, 100% test pass rate

---

## Configuration

### Environment Variables

**Root `.env`** (for Python services):
```bash
# Database connections
SOMA_PG_DSN=postgresql://omega_user:omega_dev_password@localhost:6000/omega_kg_stable
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
REDIS_URL=redis://localhost:6380

# Service ports
INGRESS_PORT=8000
INGEST_PORT=8766
OMEGA_PORT=8765
MEMOS_PORT=8768

# Auth
SOMA_INGRESS_KEY=<your-key>
```

**Cortex `.env`** (for dashboard):
```bash
VITE_API_INGRESS_URL=http://localhost:8000
VITE_API_INGEST_URL=http://localhost:8766
VITE_API_OMEGA_URL=http://localhost:8765
VITE_API_MEMOS_URL=http://localhost:8768
```

### PowerShell Parameters

```powershell
.\start_ecosystem.ps1 [OPTIONS]

Options:
  -ShowConsole         Show service console windows (debugging)
  -SkipMigrations      Skip Alembic database migrations
  -SkipContracts       Skip API contract validation
  -Persistent          Run watchdog with automatic recovery
  -LogLevel <level>    Debug | Info | Warning | Error (default: Info)
```

---

## Logs

All logs are written to `logs/` directory:

```
logs/
├── startup_YYYYMMDD_HHMMSS.log      # Main orchestrator log
├── InGress.log                       # Service stdout
├── InGress.error.log                 # Service stderr
├── InGest.log
├── InGest.error.log
├── OmegaKG.log
├── OmegaKG.error.log
├── memOS.log
├── memOS.error.log
├── Cortex.log
└── test_results_YYYYMMDD_HHMMSS.json  # Test results
```

**Log rotation**: Manual - delete old logs when folder exceeds 1GB

---

## Troubleshooting

### Services Won't Start

1. **Check prerequisites**:
   ```powershell
   docker --version
   poetry --version
   npm --version
   python --version
   ```

2. **Check Poetry environments**:
   ```powershell
   cd InGress && poetry env info
   cd InGest && poetry env info
   cd OmegaKG && poetry env info
   cd memOS && poetry env info
   ```

3. **Install dependencies**:
   ```powershell
   cd <service> && poetry install
   ```

### Docker Not Starting

```powershell
# Check Docker daemon
docker ps

# Restart Docker Desktop
Restart-Service -Name "com.docker.service"

# Check docker-compose.yml
docker compose config
```

### Health Checks Failing

1. **Check service logs**:
   ```powershell
   Get-Content logs\<service>.log -Tail 50
   Get-Content logs\<service>.error.log -Tail 50
   ```

2. **Manually test health endpoint**:
   ```powershell
   Invoke-WebRequest http://localhost:8000/health
   ```

3. **Check port conflicts**:
   ```powershell
   netstat -ano | findstr "8000 8766 8765 8768 5173"
   ```

### Cortex Not Connecting

1. **Verify `.env` configuration**:
   ```powershell
   Get-Content Cortex\.env
   ```

2. **Check CORS settings** - Python services must allow `localhost:5173`

3. **Verify all APIs healthy**:
   ```powershell
   .\test_ecosystem.ps1
   ```

### Persistent Mode Issues

- **Restart loops**: Check `logs/startup_*.log` for restart counter
- **Max attempts reached**: Service marked as Failed, manual intervention required
- **Memory leaks**: Monitor with Task Manager, restart services if RAM > 2GB per service

---

## Performance

### Startup Benchmarks

| Phase | Time | Notes |
|-------|------|-------|
| Pre-flight checks | 1-2s | Tool verification |
| Docker startup | 10-20s | First time: longer |
| Database migrations | 5-15s | Depends on schema changes |
| Contract validation | 2-5s | JSON schema checks |
| Service startup | 30-60s | All services + health checks |
| **Total** | **~60-90s** | Clean cold start |

**Warm start** (Docker already running): ~30-40s

### Resource Usage (Steady State)

| Component | CPU | RAM | Disk I/O |
|-----------|-----|-----|----------|
| Postgres | 2-5% | 200MB | Medium |
| Neo4j | 5-10% | 500MB | Medium |
| Redis | 1-2% | 50MB | Low |
| InGress | 1-3% | 150MB | Low |
| InGest | 3-8% | 500MB | Medium (spaCy models) |
| OmegaKG | 2-5% | 200MB | Medium |
| memOS | 1-3% | 150MB | Low |
| Cortex | 1-5% | 200MB | Low |
| **Total** | **~20-40%** | **~2GB** | |

*Tested on: Intel i7-10700K, 32GB RAM, NVMe SSD*

---

## Security Notes

⚠️ **Development Configuration** - NOT production-ready:
- Hardcoded passwords in `.env.example`
- No TLS/HTTPS
- No rate limiting
- Permissive CORS
- No authentication on most endpoints

**Production checklist**:
- [ ] Move secrets to environment variables or vault
- [ ] Enable TLS certificates
- [ ] Configure reverse proxy (nginx)
- [ ] Add rate limiting middleware
- [ ] Restrict CORS to specific domains
- [ ] Enable JWT authentication
- [ ] Run services under limited user accounts
- [ ] Enable firewall rules

---

## Maintenance

### Daily Operations

```powershell
# Start with monitoring
.\start_ecosystem.ps1 -Persistent

# Run health checks
.\test_ecosystem.ps1

# Verify meal trace
.\scripts\operations\trace-meal.ps1
```

### Weekly Maintenance

```powershell
# Update dependencies
cd <service> && poetry update

# Run migrations
poetry run python scripts/database/migrate_all.py upgrade

# Clear old logs
Remove-Item logs\*.log -Recurse -Force -Confirm
```

### Emergency Recovery

```powershell
# Stop all services
Get-Process | Where-Object {$_.Path -like "*poetry*" -or $_.Path -like "*npm*"} | Stop-Process -Force

# Reset Docker
docker compose down -v
docker compose up -d

# Fresh start
.\start_ecosystem.ps1 -ShowConsole -LogLevel Debug
```

---

## API Contracts

All services have defined contracts in `contracts/` directory. The startup script validates these automatically unless `-SkipContracts` is specified.

### Validate Contracts Manually
```powershell
python contracts/validate_contracts.py
```

---

## Database Migrations

Migrations run automatically during startup unless `-SkipMigrations` is specified.

### Run Migrations Manually
```powershell
# Upgrade all services
python scripts/database/migrate_all.py upgrade

# Check status
python scripts/database/migrate_all.py status

# Validate configuration
python scripts/database/migrate_all.py validate
```

---

## Support

**Logs**: Check `logs/` directory first  
**Health Status**: http://localhost:5173 (Cortex dashboard)  
**Test Suite**: `.\test_ecosystem.ps1`  
**Documentation**: See `AGENTS.md` files in each service directory

---

*Generated: 2026-01-30*  
*Soma Ecosystem v2.0 - Robust Windows 11 Edition*
