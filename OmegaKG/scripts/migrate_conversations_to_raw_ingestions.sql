-- Migration Script: raw_conversations → raw_ingestions
-- This script migrates existing conversation data from the deprecated
-- raw_conversations table to the new consolidated raw_ingestions table.
--
-- Usage:
--   psql -h 127.0.0.1 -p 6000 -U omega_user -d omegakg -f migrate_conversations_to_raw_ingestions.sql
--
-- Or via Python:
--   python -m omega_kg.database.run_migration scripts/migrate_conversations_to_raw_ingestions.sql

BEGIN;

-- Check if raw_conversations table exists and has data
DO $$
DECLARE
    table_exists BOOLEAN;
    row_count INTEGER;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'raw_conversations'
    ) INTO table_exists;

    IF NOT table_exists THEN
        RAISE NOTICE 'raw_conversations table does not exist. Nothing to migrate.';
        RETURN;
    END IF;

    SELECT COUNT(*) INTO row_count FROM raw_conversations;

    IF row_count = 0 THEN
        RAISE NOTICE 'raw_conversations table is empty. Nothing to migrate.';
        RETURN;
    END IF;

    RAISE NOTICE 'Found % records in raw_conversations. Starting migration...', row_count;
END $$;

-- Migrate existing raw_conversations to raw_ingestions
-- Maps fields:
--   id → ingestion_id
--   platform → source_type (with 'conversation-' prefix)
--   raw_payload → raw_payload
--   captured_at → captured_at
--   processed → processed
--   processed_at → processed_at
--   error → last_error
--   Sets processing_attempts = 0 for migrated records
INSERT INTO raw_ingestions (
    ingestion_id,
    source_type,
    raw_payload,
    captured_at,
    processed,
    processed_at,
    processing_attempts,
    last_error,
    created_at
)
SELECT
    id::text,
    'conversation-' || COALESCE(platform, 'unknown'),
    raw_payload,
    captured_at,
    COALESCE(processed, FALSE),
    processed_at,
    0, -- processing_attempts (default for migrated records)
    error, -- map to last_error
    captured_at -- created_at
FROM raw_conversations
ON CONFLICT (ingestion_id) DO NOTHING;

-- Get count of migrated records
DO $$
DECLARE
    migrated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO migrated_count
    FROM raw_conversations rc
    WHERE EXISTS (
        SELECT 1 FROM raw_ingestions ri
        WHERE ri.ingestion_id = rc.id::text
    );

    RAISE NOTICE 'Successfully migrated % conversation records to raw_ingestions.', migrated_count;
END $$;

-- Optionally: Create a backup of raw_conversations before dropping
-- Uncomment the following line to create a backup table:
-- CREATE TABLE raw_conversations_backup AS SELECT * FROM raw_conversations;

-- Optionally: Drop the deprecated raw_conversations table
-- Uncomment the following lines AFTER verifying the migration was successful:
-- DROP TABLE IF EXISTS raw_conversations CASCADE;

COMMIT;

-- Verification Query: Run this after migration to verify
-- SELECT source_type, COUNT(*) FROM raw_ingestions WHERE source_type LIKE 'conversation-%' GROUP BY source_type;
