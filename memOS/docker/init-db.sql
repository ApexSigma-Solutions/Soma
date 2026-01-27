-- =============================================================================
-- memOS.MCP PostgreSQL Initialization Script
-- =============================================================================
-- Creates the memos schema and required tables for vector storage
-- This script is automatically run by docker-entrypoint-initdb.d
-- =============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memos schema
CREATE SCHEMA IF NOT EXISTS memos;

-- Set search path
SET search_path TO memos, public;

-- =============================================================================
-- MEMORIES TABLE
-- =============================================================================
-- Stores content, embeddings, and metadata for all memories
CREATE TABLE IF NOT EXISTS memos.memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    agent_id VARCHAR(255) NOT NULL DEFAULT 'default_agent',
    embedding vector(1024),  -- 1024-dimensional vectors (bge-m3)
    embedding_model VARCHAR(100),
    memory_metadata JSONB,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memos.memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memos.memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memos.memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_metadata ON memos.memories USING GIN(memory_metadata);

-- Vector similarity index (IVFFLAT for efficient cosine similarity search)
-- Note: This index is created after data insertion for better performance
-- CREATE INDEX idx_memories_embedding ON memos.memories 
-- USING ivfflat (embedding vector_cosine_ops) 
-- WITH (lists = 100);

-- =============================================================================
-- MEMORY AUDIT TABLE
-- =============================================================================
-- Tracks all operations on memories for compliance and debugging
CREATE TABLE IF NOT EXISTS memos.memory_audit (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER REFERENCES memos.memories(id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,  -- 'insert', 'update', 'delete', 'search'
    agent_id VARCHAR(255),
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON memos.memory_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_memory_id ON memos.memory_audit(memory_id);
CREATE INDEX IF NOT EXISTS idx_audit_operation ON memos.memory_audit(operation);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION memos.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_memories_updated_at ON memos.memories;
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memos.memories
    FOR EACH ROW
    EXECUTE FUNCTION memos.update_updated_at_column();

-- =============================================================================
-- SAMPLE QUERIES (for testing)
-- =============================================================================

-- Search by cosine similarity (example)
-- SELECT id, content, 1 - (embedding <=> '[0.1,0.2,...]'::vector) as similarity
-- FROM memos.memories
-- WHERE agent_id = 'default_agent'
-- ORDER BY embedding <=> '[0.1,0.2,...]'::vector
-- LIMIT 10;

-- Get memory statistics
-- SELECT 
--     COUNT(*) as total_memories,
--     COUNT(DISTINCT agent_id) as unique_agents,
--     COUNT(embedding) as memories_with_embeddings,
--     pg_size_pretty(pg_total_relation_size('memos.memories')) as table_size
-- FROM memos.memories;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant usage on schema to the application user
GRANT USAGE ON SCHEMA memos TO omega_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memos TO omega_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA memos TO omega_user;

-- Ensure future tables also get permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA memos
    GRANT ALL PRIVILEGES ON TABLES TO omega_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA memos
    GRANT ALL PRIVILEGES ON SEQUENCES TO omega_user;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ memOS.MCP database initialized successfully';
    RAISE NOTICE '   - Schema: memos';
    RAISE NOTICE '   - Tables: memories, memory_audit';
    RAISE NOTICE '   - Extension: pgvector enabled';
    RAISE NOTICE '   - User: omega_user granted permissions';
END $$;
