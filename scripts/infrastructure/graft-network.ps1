# --- CONFIGURATION ---
$TargetNetwork = "apexsigma.net"

# 1. The "Old Guard" (Your Stable Data)
# These are currently isolated or on the default bridge
$StableOrgans = @(
    "apexsigma.postgres.stable",
    "apexsigma.neo4j.stable",
    "apexsigma.redis"
)

# 2. The "New Genesis" (Soma System)
# These are currently on 'soma-nervous-system'
$NewOrgans = @(
    "soma-memos", 
    "soma-omegakg", 
    "soma-ingest-daemon", 
    "soma-ingest-web"
)

Write-Host "🔄 INITIATING GRAND UNIFICATION PROTOCOL..." -ForegroundColor Cyan
Write-Host "   Target Network: $TargetNetwork" -ForegroundColor Gray

# --- STEP 1: ENSURE NETWORK EXISTS ---
if (!(docker network ls -q -f name=$TargetNetwork)) {
    Write-Host "⚡ Creating network '$TargetNetwork'..."
    docker network create $TargetNetwork
}
else {
    Write-Host "✅ Network '$TargetNetwork' exists." -ForegroundColor Green
}

# --- STEP 2: CONNECT STABLE ORGANS ---
Write-Host "`n🔗 Connecting Stable Infrastructure..."
foreach ($container in $StableOrgans) {
    if (docker ps -q -f name=$container) {
        try {
            docker network connect $TargetNetwork $container 2>$null
            Write-Host "   ✅ $container attached." -ForegroundColor Green
        }
        catch {
            Write-Host "   ℹ️  $container already connected." -ForegroundColor DarkGray
        }
    }
    else {
        Write-Host "   ⚠️  $container NOT FOUND/RUNNING. Please start your stable stack." -ForegroundColor Yellow
    }
}

# --- STEP 3: CONNECT NEW SOMA ORGANS ---
Write-Host "`n🔗 Connecting Soma Genesis Organs..."
foreach ($container in $NewOrgans) {
    if (docker ps -q -f name=$container) {
        try {
            docker network connect $TargetNetwork $container 2>$null
            Write-Host "   ✅ $container attached." -ForegroundColor Green
        }
        catch {
            Write-Host "   ℹ️  $container already connected." -ForegroundColor DarkGray
        }
    }
    else {
        Write-Host "   ⚠️  $container NOT FOUND. Run 'docker compose up -d' first." -ForegroundColor Yellow
    }
}

# --- STEP 4: VERIFICATION ---
Write-Host "`n🔍 Verifying Topology..."
$members = docker network inspect $TargetNetwork -f '{{range .Containers}}{{.Name}} {{end}}'
Write-Host "   Members of $TargetNetwork : $members" -ForegroundColor Gray

# --- STEP 5: INSTRUCTIONS ---
Write-Host "`n🎉 NETWORK GRAFT COMPLETE." -ForegroundColor Cyan
Write-Host "   The Brain and Hands can now talk to the Stable Memory directly."
Write-Host "`n⚠️  CRITICAL NEXT STEP: Restart 'memOS' with these variables:" -ForegroundColor Magenta
Write-Host "   --------------------------------------------------------"
Write-Host "   POSTGRES_HOST=apexsigma.postgres.stable"
Write-Host "   POSTGRES_PORT=5432"
Write-Host "   MEMOS_REDIS_HOST=apexsigma.redis"
Write-Host "   MEMOS_REDIS_PORT=6379"
Write-Host "   NEO4J_URI=bolt://apexsigma.neo4j.stable:7687"
Write-Host "   --------------------------------------------------------"
Write-Host "   Command to apply fix immediately:"
Write-Host '   $Env:POSTGRES_HOST="apexsigma.postgres.stable"; $Env:POSTGRES_PORT="5432"; $Env:MEMOS_REDIS_HOST="apexsigma.redis"; docker restart soma-memos' -ForegroundColor Yellow