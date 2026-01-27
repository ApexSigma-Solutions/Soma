-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create main vector storage table
CREATE TABLE IF NOT EXISTS omega_vectors_1024 (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL,
    embedding vector(1024),
    status TEXT NOT NULL DEFAULT 'pending_embedding',
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('pending_embedding', 'ready', 'failed'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_omega_vectors_message_id ON omega_vectors_1024(message_id);
CREATE INDEX IF NOT EXISTS idx_omega_vectors_status ON omega_vectors_1024(status);
CREATE INDEX IF NOT EXISTS idx_omega_vectors_pending ON omega_vectors_1024(message_id) WHERE status = 'pending_embedding';
CREATE INDEX IF NOT EXISTS idx_omega_vectors_cleanup ON omega_vectors_1024(updated_at) WHERE status = 'pending_embedding';
CREATE INDEX IF NOT EXISTS idx_omega_vectors_failed_retry ON omega_vectors_1024(retry_count, updated_at) WHERE status = 'failed';
CREATE INDEX IF NOT EXISTS idx_omega_vectors_embedding_hnsw ON omega_vectors_1024 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Verify table was created
SELECT 'Table omega_vectors_1024 created successfully' AS status;
SELECT COUNT(*) AS index_count FROM pg_indexes WHERE tablename = 'omega_vectors_1024';
