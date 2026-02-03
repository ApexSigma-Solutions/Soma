# Soma Ecosystem - Quick Reference

## ✅ All Issues Fixed - Ready to Start!

### 🎯 What Was Fixed
1. ✅ Poetry configuration errors
2. ✅ Docker Compose migration (manual → orchestrated)
3. ✅ SSL/Certificate issues (certifi path)
4. ✅ Port security (0.0.0.0 → 127.0.0.1)

---

## 🚀 Quick Start Commands

### Check Docker Status
```powershell
docker compose ps
```
**Expected:** All 3 services showing "healthy"

### Start Ecosystem (Automated)
```powershell
.\start_ecosystem.ps1
```

### Manual Startup (Step-by-Step)
```powershell
# 1. Ensure Docker is running
docker compose ps

# 2. Run migrations
.\scripts\utils\poetry-fix.ps1 run python scripts/database/migrate_all.py upgrade

# 3. Start ecosystem
.\start_ecosystem.ps1
```

---

## 🛠️ Important Tools Created

### Poetry SSL/Certificate Fix
```powershell
# Use this instead of 'poetry <command>':
.\scripts\utils\poetry-fix.ps1 <command>

# Examples:
.\scripts\utils\poetry-fix.ps1 install
.\scripts\utils\poetry-fix.ps1 lock
.\scripts\utils\poetry-fix.ps1 run python script.py
```

### Docker Migration Script
```powershell
# Migrate manual containers → Docker Compose
.\scripts\infrastructure\migrate-to-compose.ps1

# Dry run (preview only):
.\scripts\infrastructure\migrate-to-compose.ps1 -DryRun
```

---

## 📍 Service Endpoints

| Service       | URL                              |
|---------------|----------------------------------|
| Cortex        | http://localhost:5173            |
| InGress API   | http://localhost:8000/docs       |
| InGest Web    | http://localhost:3000            |
| OmegaKG API   | http://localhost:8765/docs       |
| memOS API     | http://localhost:8768/docs       |
| Neo4j Browser | http://localhost:7474            |
| Postgres      | localhost:6000 (psql/pgAdmin)    |
| Redis         | localhost:6380 (redis-cli)       |

---

## 🔍 Troubleshooting One-Liners

```powershell
# Check what's running
docker compose ps

# View service logs
docker compose logs <service-name>

# Restart a service
docker compose restart <service-name>

# Restart all infrastructure
docker compose restart postgres neo4j redis

# Test ports
Test-NetConnection localhost -Port 6000  # Postgres
Test-NetConnection localhost -Port 7687  # Neo4j
Test-NetConnection localhost -Port 6380  # Redis
```

---

## 📚 Documentation

- **Full Migration Report:** `docs/migration/docker-compose-migration-2026-02-02.md`
- **Issue Resolution Guide:** `docs/migration/startup-issues-resolved.md`
- **Quick Reference:** `docs/migration/quick-reference.md` (this file)

---

## 💡 Pro Tips

1. **Always use `poetry-fix.ps1`** for Poetry commands
2. **Check Docker health first** before starting application services
3. **Backups are in** `backups/volumes_20260202_222211/` (just in case)
4. **Services bind to localhost only** (127.0.0.1) for security

---

## ⚡ One-Command Health Check

```powershell
docker compose ps && echo "=== Port Tests ===" && Test-NetConnection localhost -Port 6000 -InformationLevel Quiet && Write-Host "✓ Postgres OK" || Write-Host "✗ Postgres FAIL" && Test-NetConnection localhost -Port 7687 -InformationLevel Quiet && Write-Host "✓ Neo4j OK" || Write-Host "✗ Neo4j FAIL" && Test-NetConnection localhost -Port 6380 -InformationLevel Quiet && Write-Host "✓ Redis OK" || Write-Host "✗ Redis FAIL"
```

---

**Status:** 🟢 **ALL SYSTEMS GO**  
**Next:** Run `.\start_ecosystem.ps1`
