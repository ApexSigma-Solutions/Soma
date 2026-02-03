-- =============================================================================
-- Migration: Add processing_status enum to raw_lake
-- =============================================================================
-- Replaces boolean 'processed' column with enum-based status tracking
-- Required for SimpleMem v2.0 digestion pipeline
-- =============================================================================

-- Create status enum type
DO $$ BEGIN
    CREATE TYPE raw_lake_status AS ENUM ('PENDING', 'DIGESTED', 'ERROR');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add processing_status column
ALTER TABLE raw_lake
ADD COLUMN IF NOT EXISTS processing_status raw_lake_status DEFAULT 'PENDING';

-- Add processed_at timestamp
ALTER TABLE raw_lake
ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE;

-- Add last_error column for debugging
ALTER TABLE raw_lake
ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Migrate existing data: processed=true -> DIGESTED, processed=false -> PENDING
UPDATE raw_lake 
SET processing_status = CASE 
    WHEN processed = TRUE THEN 'DIGESTED'::raw_lake_status 
    ELSE 'PENDING'::raw_lake_status 
END
WHERE processing_status IS NULL;

-- Add created_at column (maps to ingested_at for Dagster)
ALTER TABLE raw_lake
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE;

-- Backfill created_at from ingested_at
UPDATE raw_lake 
SET created_at = ingested_at 
WHERE created_at IS NULL;

-- Create index for new polling pattern
CREATE INDEX IF NOT EXISTS idx_raw_lake_pending 
ON raw_lake (created_at) WHERE processing_status = 'PENDING';

COMMENT ON COLUMN raw_lake.processing_status IS 'SimpleMem v2.0 status: PENDING, DIGESTED, ERROR';
COMMENT ON COLUMN raw_lake.processed_at IS 'Timestamp when record was digested and pushed to Redis';
COMMENT ON COLUMN raw_lake.last_error IS 'Error message if processing failed';
