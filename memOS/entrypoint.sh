#!/bin/sh
set -e

# =============================================================================
# SOMA MEMOS (THE HANDS) - ENTRYPOINT SCRIPT
# =============================================================================
# This script performs connectivity checks before launching the app.
# It ensures all required services (Postgres, Redis, Neo4j) are reachable.
# =============================================================================

# --- CONFIGURATION ---
# Use environment variables passed from docker-compose.yml
PG_HOST="${POSTGRES_HOST:-apexsigma.postgres.stable}"
PG_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${MEMOS_REDIS_HOST:-apexsigma.redis}"
REDIS_PORT="${MEMOS_REDIS_PORT:-6379}"
NEO4J_HOST="${NEO4J_URI:-bolt://apexsigma.neo4j.stable:7687}"

# Extract Neo4j hostname from URI (bolt://hostname:port -> hostname)
NEO4J_HOSTNAME=$(echo "$NEO4J_HOST" | sed -E 's|^bolt://([^:]+):.*|\1|')
NEO4J_PORT=7687

MAX_RETRIES=30
RETRY_INTERVAL=3

echo "================================================="
echo "🖐️  [memOS] SOMA-HANDS INITIALIZATION"
echo "   Database:  $PG_HOST:$PG_PORT"
echo "   Redis:     $REDIS_HOST:$REDIS_PORT"
echo "   Neo4j:     $NEO4J_HOSTNAME:$NEO4J_PORT"
echo "================================================="

# --- FUNCTION: Wait for service ---
wait_for_service() {
    local name=$1
    local host=$2
    local port=$3
    local attempt=0

    echo "⏳ [memOS] Waiting for $name ($host:$port)..."

    # First, verify DNS resolution
    if ! getent hosts "$host" > /dev/null 2>&1; then
        echo "   ⚠️  DNS lookup for '$host' failed. Waiting for Docker DNS..."
    fi

    while ! nc -z -w 2 "$host" "$port" 2>/dev/null; do
        attempt=$((attempt + 1))

        if [ "$attempt" -gt "$MAX_RETRIES" ]; then
            echo "❌ [memOS] FATAL: Timeout waiting for $name ($host:$port)"
            echo "   Debug: Attempting DNS lookup..."
            getent hosts "$host" || echo "   DNS resolution failed for $host"
            exit 1
        fi

        if [ "$attempt" -eq 1 ] || [ $((attempt % 5)) -eq 0 ]; then
            echo "   ⚠️  $name not ready (Attempt $attempt/$MAX_RETRIES)"
        fi

        sleep "$RETRY_INTERVAL"
    done

    echo "✅ [memOS] $name is READY."
}

# --- STEP 1: HOST DNS PATCHING (Conditional) ---
# Only runs if we are explicitly told to connect to the Windows Host
if [ "$PG_HOST" = "host.docker.internal" ] || [ "$REDIS_HOST" = "host.docker.internal" ]; then
    echo "🔧 [memOS] Configuration points to Host Machine. Checking DNS..."
    if ! getent hosts "host.docker.internal" > /dev/null 2>&1; then
        echo "   ⚠️ 'host.docker.internal' not resolving. Patching /etc/hosts..."
        HOST_IP=$(ip route show | awk '/default/ {print $3}')
        if [ -n "$HOST_IP" ]; then
            echo "$HOST_IP host.docker.internal" >> /etc/hosts
            echo "   ✅ Patched Host IP: $HOST_IP"
        else
            echo "   ❌ Failed to detect gateway IP."
        fi
    fi
fi

# --- STEP 2: CONNECTIVITY CHECKS ---
wait_for_service "PostgreSQL" "$PG_HOST" "$PG_PORT"
wait_for_service "Redis" "$REDIS_HOST" "$REDIS_PORT"
wait_for_service "Neo4j" "$NEO4J_HOSTNAME" "$NEO4J_PORT"

echo "================================================="
echo "🚀 [memOS] All services READY. Starting application..."
echo "================================================="

# --- STEP 3: LAUNCH APP ---
exec "$@"