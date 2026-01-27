-- Migration: 001_create_memos_schema.sql
-- Description: Create memos schema with pgvector support for memory storage
-- Date: 2026-01-03
-- TNP: TNP-MEM-300

-- =============================================================================
-- SCHEMA CREATION
-- =============================================================================

-- Create memos schema
CREATE SCHEMA IF NOT EXISTS memos;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Create memories table with vector support
CREATE TABLE IF NOT EXISTS memos.memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    agent_id VARCHAR(255) NOT NULL DEFAULT 'default_agent',
    memory_metadata JSONB,
    embedding vector(1024),
    embedding_model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags TEXT[]
);

-- Create memory_audit table for operation logging
CREATE TABLE IF NOT EXISTS memos.memory_audit (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER,
    operation VARCHAR(20) NOT NULL,
    agent_id VARCHAR(255),
    details JSONB,
    performed_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Agent ID index for filtering by agent
CREATE INDEX IF NOT EXISTS idx_memories_agent_id 
    ON memos.memories(agent_id);

-- Timestamp index for time-based queries
CREATE INDEX IF NOT EXISTS idx_memories_created_at 
    ON memos.memories(created_at DESC);

-- GIN index for tag-based queries
CREATE INDEX IF NOT EXISTS idx_memories_tags 
    ON memos.memories USING GIN(tags);

-- IVFFLAT index for vector similarity search
-- Note: This index requires data to be present for optimal list count
-- Using 100 lists as starting point, suitable for up to ~100k vectors
CREATE INDEX IF NOT EXISTS idx_memories_embedding 
    ON memos.memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Audit table indexes
CREATE INDEX IF NOT EXISTS idx_audit_memory_id 
    ON memos.memory_audit(memory_id);

CREATE INDEX IF NOT EXISTS idx_audit_performed_at 
    ON memos.memory_audit(performed_at DESC);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION memos.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Trigger to automatically update updated_at on row update
DROP TRIGGER IF EXISTS update_memories_updated_at ON memos.memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memos.memories
    FOR EACH ROW
    EXECUTE FUNCTION memos.update_updated_at_column();

-- =============================================================================
-- GRANTS (optional, uncomment if using separate roles)
-- =============================================================================
-- GRANT USAGE ON SCHEMA memos TO memos_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memos TO memos_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA memos TO memos_user;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- Run these queries to verify the migration:
-- SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'memos';
-- \dt memos.*
-- \di memos.*
