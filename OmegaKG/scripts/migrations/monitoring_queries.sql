-- =============================================================================
-- Omega_KG Vector Storage Monitoring Queries
-- =============================================================================
-- Purpose: Operational visibility and debugging for omega_vectors_1024
-- Use Cases:
--   - Worker health monitoring
--   - Failure detection and alerting
--   - TTL-based cleanup
--   - Performance analysis
--
-- Note: All queries are read-only and safe for production dashboards
-- =============================================================================


-- =============================================================================
-- WORKER HEALTH MONITORING
-- =============================================================================

-- Query 1: Pending Embeddings by Message
-- Purpose: Check how many pending embeddings exist per message
-- Use: Worker diagnostics, bottleneck detection
-- Alert Threshold: > 1000 pending (indicates worker stall or Ollama issue)
SELECT
    message_id,
    COUNT(*) AS pending_count,
    MAX(created_at) AS oldest_pending,
    NOW() - MAX(created_at) AS age_duration
FROM omega_vectors_1024
WHERE status = 'pending_embedding'
GROUP BY message_id
ORDER BY pending_count DESC, age_duration DESC
LIMIT 20;


-- Query 2: Global Embedding Statistics
-- Purpose: High-level overview of vector storage health
-- Use: Dashboard, alerting on anomalies
SELECT
    status,
    COUNT(*) AS count,
    AVG(retry_count) AS avg_retries,
    MAX(retry_count) AS max_retries,
    MIN(created_at) AS oldest_record,
    MAX(updated_at) AS most_recent_update
FROM omega_vectors_1024
GROUP BY status
ORDER BY count DESC;


-- Query 3: Pending vs Ready Ratio
-- Purpose: Quick health check of vector generation progress
-- Use: At-a-glance worker performance
WITH stats AS (
    SELECT
        COUNT(CASE WHEN status = 'pending_embedding' THEN 1 END) AS pending,
        COUNT(CASE WHEN status = 'ready' THEN 1 END) AS ready,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed,
        COUNT(*) AS total
    FROM omega_vectors_1024
)
SELECT
    pending,
    ready,
    failed,
    total,
    ROUND(CAST(pending AS NUMERIC) / total * 100, 2) AS pending_pct,
    ROUND(CAST(ready AS NUMERIC) / total * 100, 2) AS ready_pct,
    ROUND(CAST(failed AS NUMERIC) / total * 100, 2) AS failed_pct
FROM stats;


-- =============================================================================
-- FAILURE DETECTION & ALERTING
-- =============================================================================

-- Query 4: Failed Records Requiring Intervention
-- Purpose: Identify persistently failed embeddings
-- Use: Alerting system, manual retry queue
-- Action: Inspect these records and either retry or investigate Ollama issue
SELECT
    id,
    message_id,
    retry_count,
    created_at,
    updated_at,
    NOW() - updated_at AS time_since_last_attempt,
    CASE
        WHEN retry_count >= 3 THEN 'CRITICAL: Max retries exceeded'
        WHEN retry_count >= 2 THEN 'WARNING: Near max retries'
        ELSE 'INFO: Needs retry'
    END AS severity
FROM omega_vectors_1024
WHERE status = 'failed'
ORDER BY retry_count DESC, updated_at DESC
LIMIT 50;


-- Query 5: Stale Pending Records (Worker Stall Detection)
-- Purpose: Find pending embeddings stuck for abnormally long times
-- Use: Alert on worker hang, Ollama disconnect, or infinite loop
-- Threshold: 1 hour (configurable based on your workload)
SELECT
    id,
    message_id,
    created_at,
    updated_at,
    NOW() - created_at AS pending_duration,
    retry_count,
    CASE
        WHEN NOW() - created_at > INTERVAL '2 hours' THEN 'CRITICAL: Very stale'
        WHEN NOW() - created_at > INTERVAL '1 hour' THEN 'WARNING: Stale'
        ELSE 'INFO: Normal'
    END AS severity
FROM omega_vectors_1024
WHERE status = 'pending_embedding'
    AND NOW() - created_at > INTERVAL '30 minutes'
ORDER BY pending_duration DESC
LIMIT 50;


-- Query 6: High Retry Count Distribution
-- Purpose: Understand failure patterns
-- Use: Identify systemic issues vs one-off failures
SELECT
    retry_count,
    COUNT(*) AS count,
    ROUND(CAST(COUNT(*) AS NUMERIC) / (SELECT COUNT(*) FROM omega_vectors_1024 WHERE status IN ('failed', 'pending_embedding')) * 100, 2) AS pct
FROM omega_vectors_1024
WHERE status IN ('failed', 'pending_embedding')
GROUP BY retry_count
ORDER BY retry_count DESC;


-- =============================================================================
-- TTL-BASED CLEANUP & MAINTENANCE
-- =============================================================================

-- Query 7: Identify Records Eligible for Cleanup
-- Purpose: Find pending records older than TTL (default: 7 days)
-- Use: Before running cleanup, preview what will be deleted
-- TTL: Configurable via VECTOR_CLEANUP_TTL_DAYS in config.py
SELECT
    id,
    message_id,
    created_at,
    updated_at,
    NOW() - updated_at AS age,
    status,
    retry_count
FROM omega_vectors_1024
WHERE status = 'pending_embedding'
    AND updated_at < NOW() - INTERVAL '7 days'
ORDER BY updated_at ASC
LIMIT 100;


-- Query 8: Cleanup Dry-Run (Count Only)
-- Purpose: Preview how many records will be deleted before executing cleanup
-- Use: Validate cleanup logic before production run
SELECT
    COUNT(*) AS records_to_delete,
    MIN(updated_at) AS oldest_record,
    MAX(updated_at) AS newest_record,
    NOW() - MIN(updated_at) AS age_of_oldest
FROM omega_vectors_1024
WHERE status = 'pending_embedding'
    AND updated_at < NOW() - INTERVAL '7 days';


-- Query 9: Cleanup Execution (DESTRUCTIVE - Use with Caution)
-- Purpose: Delete stale pending records
-- Use: Run periodically (e.g., nightly) via background job
-- Safety: Only targets pending_embedding status; does NOT affect failed or ready
-- BACKUP FIRST: Consider backing up table before running in production
--
-- Execution (commented out by default):
-- DELETE FROM omega_vectors_1024
-- WHERE status = 'pending_embedding'
--   AND updated_at < NOW() - INTERVAL '7 days';


-- =============================================================================
-- PERFORMANCE & CAPACITY ANALYSIS
-- =============================================================================

-- Query 10: Table Size and Index Statistics
-- Purpose: Understand storage footprint
-- Use: Capacity planning, performance tuning
SELECT
    'omega_vectors_1024' AS table_name,
    pg_size_pretty(pg_total_relation_size('omega_vectors_1024')) AS total_size,
    pg_size_pretty(pg_relation_size('omega_vectors_1024')) AS table_size,
    pg_size_pretty(pg_total_relation_size('omega_vectors_1024') - pg_relation_size('omega_vectors_1024')) AS indexes_size,
    (SELECT COUNT(*) FROM omega_vectors_1024) AS row_count;


-- Query 11: Index Usage Statistics
-- Purpose: Identify unused or underutilized indexes
-- Use: Maintenance optimization, index removal
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelname::regclass)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename = 'omega_vectors_1024'
ORDER BY idx_scan DESC;


-- Query 12: Missing Indexes (Slow Queries Analysis)
-- Purpose: Detect seq scans that could be optimized with new indexes
-- Use: Query performance tuning
SELECT
    schemaname,
    tablename,
    seq_scan AS sequential_scans,
    seq_tup_read AS tuples_from_seq_scan,
    idx_scan AS index_scans,
    seq_tup_read - idx_scan AS wasted_scans
FROM pg_stat_user_tables
WHERE tablename = 'omega_vectors_1024';


-- =============================================================================
-- DEBUGGING & DIAGNOSTICS
-- =============================================================================

-- Query 13: Sample Recent Records (All Statuses)
-- Purpose: Quick inspection of table contents
-- Use: Debugging, data validation
SELECT
    id,
    message_id,
    status,
    retry_count,
    embedding IS NOT NULL AS has_embedding,
    created_at,
    updated_at,
    NOW() - updated_at AS age
FROM omega_vectors_1024
ORDER BY created_at DESC
LIMIT 20;


-- Query 14: Embedding Vector Statistics (for Ready Records)
-- Purpose: Validate embedding quality and dimensions
-- Use: Debug embedding generation issues
SELECT
    id,
    message_id,
    array_length(embedding::float8[], 1) AS embedding_dims,
    status,
    created_at
FROM omega_vectors_1024
WHERE status = 'ready'
    AND embedding IS NOT NULL
LIMIT 10;


-- Query 15: Message IDs with Multiple Embeddings (Deduplication Check)
-- Purpose: Detect duplicate embeddings for same message_id
-- Use: Data quality validation, dedup if needed
SELECT
    message_id,
    COUNT(*) AS embedding_count,
    array_agg(id) AS embedding_ids,
    array_agg(status) AS statuses
FROM omega_vectors_1024
GROUP BY message_id
HAVING COUNT(*) > 1
ORDER BY embedding_count DESC
LIMIT 50;


-- =============================================================================
-- RECOMMENDED MONITORING SCHEDULE
-- =============================================================================
-- Every 5 minutes:  Query 2 (global stats) + Query 3 (pending/ready ratio)
-- Every hour:      Query 5 (stale pending) + Query 6 (retry distribution)
-- Daily:           Query 4 (failed records) + Query 10 (table size)
-- Weekly:          Query 11 (index usage) + Query 15 (dedup check)
-- As-needed:       Query 7-8 (cleanup preview) before Query 9 (cleanup execution)
--
-- Alert Rules (Suggested):
--   - Alert if pending_pct > 50% for 30 min
--   - Alert if failed_count > 100
--   - Alert if stale pending records > 10 (Query 5)
--   - Alert if seq_scan > 1000 on table (Query 12)
-- =============================================================================
