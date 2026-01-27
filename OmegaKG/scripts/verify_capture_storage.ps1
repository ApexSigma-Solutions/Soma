#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify that captures are stored in pgvector, Neo4j, and the Obsidian vault

.DESCRIPTION
    Tests the complete capture storage pipeline across all three systems:
    1. Neo4j - ChatSession and Decision nodes
    2. PostgreSQL/pgvector - Embedding vectors and metadata
    3. Obsidian Vault - Markdown files with frontmatter
#>

$ErrorActionPreference = "Stop"

# Load .env configuration
$envFile = "D:\projects\Omega_KG_stable\.env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

$env_vars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    if ($_ -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        $env_vars[$key] = $value
    }
}

$NEO4J_USER = $env_vars['NEO4J_USER'] ?? 'neo4j'
$NEO4J_PASSWORD = $env_vars['NEO4J_PASSWORD'] ?? 'aDQUU5$@1dpuj5'
$NEO4J_URI = $env_vars['NEO4J_URI'] ?? 'bolt://localhost:7687'
$POSTGRES_USER = $env_vars['POSTGRES_USER'] ?? 'omega_user'
$POSTGRES_PASSWORD = $env_vars['POSTGRES_PASSWORD'] ?? ''
$POSTGRES_SERVER = $env_vars['POSTGRES_SERVER'] ?? '127.0.0.1'
$POSTGRES_PORT = $env_vars['POSTGRES_PORT'] ?? '5433'
$POSTGRES_DB = $env_vars['POSTGRES_DB'] ?? 'omega_kg_stable'
$VAULT_PATH = $env_vars['VAULT_PATH'] ?? 'D:\projects\omegavault.as'

Write-Host "=== Omega_KG Capture Storage Verification ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Vault Storage
Write-Host "1. OBSIDIAN VAULT STORAGE" -ForegroundColor Yellow
$vaultPath = "$VAULT_PATH/AI_Conversations"
if (Test-Path $vaultPath) {
    $conversationFiles = Get-ChildItem -Path $vaultPath -Recurse -Filter "*.md" -ErrorAction SilentlyContinue
    $fileCount = ($conversationFiles | Measure-Object).Count
    Write-Host "   ✓ Vault path exists: $vaultPath"
    Write-Host "   ✓ Found $fileCount conversation markdown files"

    if ($fileCount -gt 0) {
        Write-Host "   Sample files:"
        $conversationFiles | Select-Object -First 3 | ForEach-Object {
            Write-Host "     - $($_.Name)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "   ✗ Vault path not found: $vaultPath" -ForegroundColor Red
}
Write-Host ""

# 2. Check Neo4j Storage
Write-Host "2. NEO4J GRAPH DATABASE" -ForegroundColor Yellow
try {
    $cypher_query = "MATCH (cs:ChatSession) RETURN COUNT(cs) as count"
    $result = & docker exec apexsigma.neo4j.stable cypher-shell -u $NEO4J_USER -p "$NEO4J_PASSWORD" "$cypher_query" 2>&1 | Select-String -Pattern "^\d+"

    if ($result) {
        $chatCount = [int]($result.ToString().Trim())
        Write-Host "   ✓ Neo4j connected"
        Write-Host "   ✓ Found $chatCount ChatSession nodes" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Could not query Neo4j" -ForegroundColor Red
    }

    # Check Decision nodes
    $decision_query = "MATCH (d:Decision) RETURN COUNT(d) as count"
    $result2 = & docker exec apexsigma.neo4j.stable cypher-shell -u $NEO4J_USER -p "$NEO4J_PASSWORD" "$decision_query" 2>&1 | Select-String -Pattern "^\d+"

    if ($result2) {
        $decisionCount = [int]($result2.ToString().Trim())
        Write-Host "   ✓ Found $decisionCount Decision nodes" -ForegroundColor Green
    }

    # Sample recent ChatSessions
    $sample_query = "MATCH (cs:ChatSession) RETURN cs.id, cs.platform, cs.created_at ORDER BY cs.created_at DESC LIMIT 3"
    Write-Host "   Recent ChatSessions:"
    $samples = & docker exec apexsigma.neo4j.stable cypher-shell -u $NEO4J_USER -p "$NEO4J_PASSWORD" "$sample_query" 2>&1
    $samples | Where-Object { $_ -match '\|' -and $_ -notmatch 'id.*platform|^[\s\+\-]*$|^$' } | ForEach-Object {
        Write-Host "     $($_)" -ForegroundColor Green
    }
} catch {
    Write-Host "   ✗ Error querying Neo4j: $_" -ForegroundColor Red
}
Write-Host ""

# 3. Check PostgreSQL/pgvector Storage
Write-Host "3. POSTGRESQL VECTOR DATABASE" -ForegroundColor Yellow
try {
    # Check if tables exist
    $psql_cmd = "psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_SERVER -p $POSTGRES_PORT -t -c `"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;`" 2>&1"
    $tables = Invoke-Expression $psql_cmd -ErrorAction SilentlyContinue

    if ($tables) {
        Write-Host "   ✓ PostgreSQL connected"
        Write-Host "   ✓ Found tables:"
        $tables | Where-Object { $_ -match '\w' } | ForEach-Object {
            Write-Host "     - $_" -ForegroundColor Green
        }

        # Check for vector/embedding data if tables exist
        $vector_check = "psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_SERVER -p $POSTGRES_PORT -t -c `"SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE '%embedding%' OR table_name LIKE '%vector%';`" 2>&1"
        $vector_count = Invoke-Expression $vector_check -ErrorAction SilentlyContinue
        if ($vector_count -match "1") {
            Write-Host "   ✓ Vector/embedding storage detected"
        }
    } else {
        Write-Host "   ⚠ PostgreSQL accessible but no tables found yet (may be normal on first run)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠ PostgreSQL check skipped (psql not in PATH or connection failed)" -ForegroundColor Yellow
}
Write-Host ""

# 4. Health Check Summary
Write-Host "4. SYSTEM HEALTH CHECK" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8002/health" -ErrorAction SilentlyContinue
    Write-Host "   ✓ Capture Server: $($health.status)"
    Write-Host "   ✓ Neo4j Connected: $($health.neo4j_connected)"
    Write-Host "   ✓ PostgreSQL Connected: $($health.postgres_connected)"
    Write-Host "   ✓ Vault Accessible: $($health.vault_accessible)"
} catch {
    Write-Host "   ✗ Capture server not responding on http://127.0.0.1:8002/health" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
