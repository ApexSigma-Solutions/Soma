-- Migration: Add node_label column for polymorphic Neo4j tracking
-- Version: 1.0.1
-- Created: 2025-12-02
-- Purpose: Enable tracking of source Neo4j node type (ChatMessage, LinearIssue, Decision)
--          alongside message_id for clean joins and filtering

-- ============================================================================
-- PHASE 2: ADD NODE LABEL TRACKING COLUMN
-- ============================================================================

-- Add node_label column with sensible default for backward compatibility
ALTER TABLE omega_vectors_1024
ADD COLUMN node_label TEXT NOT NULL DEFAULT 'ChatMessage';

-- Create index for node_label filtering (enables type-specific queries)
CREATE INDEX idx_omega_vectors_node_label ON omega_vectors_1024(node_label);

-- Create compound index for Neo4j lookup pattern (message_id + node_label)
-- Used by polling queries to fetch type-specific pending records
CREATE UNIQUE INDEX idx_omega_vectors_neo4j_lookup
    ON omega_vectors_1024(message_id, node_label);

-- Drop old message_id index if unique constraint was added
-- (The new compound index replaces it for uniqueness)
-- This allows multiple message_ids with different node_labels
DROP INDEX IF EXISTS idx_omega_vectors_message_id;

-- Update index definition for performance (now using compound index)
-- The idx_omega_vectors_neo4j_lookup serves both:
-- 1. Uniqueness constraint (prevent duplicate embeddings per (message_id, node_label) pair)
-- 2. Fast lookup for polling queries

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================
-- To reverse this migration, run:
--
-- DROP INDEX IF EXISTS idx_omega_vectors_neo4j_lookup;
-- DROP INDEX IF EXISTS idx_omega_vectors_node_label;
-- ALTER TABLE omega_vectors_1024 DROP COLUMN node_label;
-- CREATE INDEX idx_omega_vectors_message_id ON omega_vectors_1024(message_id);
-- ============================================================================

-- Verify migration
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'omega_vectors_1024' AND column_name = 'node_label';

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'omega_vectors_1024' AND indexname IN (
    'idx_omega_vectors_node_label',
    'idx_omega_vectors_neo4j_lookup'
);
