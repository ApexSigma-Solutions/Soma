-- ============================================================================= 
-- Neo4j Vector Index Configuration for Soma Organism
-- ============================================================================= 
-- Creates 768-dimensional vector indexes for all entity types
-- Embedding model: Qwen3-Embedding (768 dimensions)
-- Similarity function: Cosine
-- =============================================================================

-- Person entities (name, role, affiliations, etc.)
CREATE VECTOR INDEX soma_person_embedding IF NOT EXISTS 
FOR (n:Person) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Organization entities (companies, teams, institutions)
CREATE VECTOR INDEX soma_org_embedding IF NOT EXISTS 
FOR (n:Organization) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Place entities (locations, regions, addresses)
CREATE VECTOR INDEX soma_place_embedding IF NOT EXISTS 
FOR (n:Place) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Concept entities (ideas, abstractions, topics)
CREATE VECTOR INDEX soma_concept_embedding IF NOT EXISTS 
FOR (n:Concept) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Object entities (physical items, files, artifacts)
CREATE VECTOR INDEX soma_object_embedding IF NOT EXISTS 
FOR (n:Object) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Technology entities (tools, frameworks, systems)
CREATE VECTOR INDEX soma_tech_embedding IF NOT EXISTS 
FOR (n:Technology) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- Language entities (programming languages, natural languages)
CREATE VECTOR INDEX soma_lang_embedding IF NOT EXISTS 
FOR (n:Language) ON n.embedding 
OPTIONS {indexConfig: {
  `vector.dimensions`: 768, 
  `vector.similarity_function`: 'cosine'
}};

-- =============================================================================
-- Verification Query
-- =============================================================================
-- Run this after creating indexes to verify they are ONLINE:
-- SHOW INDEXES WHERE type = 'VECTOR';
