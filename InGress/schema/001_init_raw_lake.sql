-- =============================================================================
-- Soma.Ingress: Raw Lake Schema
-- =============================================================================
-- Purpose: Buffer table for all incoming sensory data before processing
-- Target:  omega_kg_stable database on Postgres
-- =============================================================================

-- Raw Lake Table for Soma.Ingress
CREATE TABLE IF NOT EXISTS raw_lake (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(64) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    client_ip VARCHAR(45),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

-- Index for efficient polling by InGest (unprocessed records)
CREATE INDEX IF NOT EXISTS idx_raw_lake_unprocessed 
ON raw_lake (ingested_at) WHERE processed = FALSE;

-- Index for source-based queries
CREATE INDEX IF NOT EXISTS idx_raw_lake_source ON raw_lake (source);

-- Index for event type filtering
CREATE INDEX IF NOT EXISTS idx_raw_lake_event_type ON raw_lake (event_type);

COMMENT ON TABLE raw_lake IS 'Soma.Ingress sensory buffer - raw captured data awaiting digestion';
COMMENT ON COLUMN raw_lake.source IS 'Origin of data: obsidian, github, chrome, terminal';
COMMENT ON COLUMN raw_lake.event_type IS 'Type of event: file_mod, push, web_capture, command_log';
COMMENT ON COLUMN raw_lake.processed IS 'Flag for InGest poller acknowledgment';
