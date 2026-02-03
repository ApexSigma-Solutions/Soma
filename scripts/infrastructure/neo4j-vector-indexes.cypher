# Neo4j Vector Index Setup for Soma Brain

Run these Cypher commands in Neo4j Browser or via `cypher-shell`:

```sh
docker exec -it apexsigma.neo4j.soma cypher-shell -u omega_user -p omega_dev_password
```

## Variable Entity Vector Indexes

```cypher
-- Create vector indexes for each entity type (768-dim, cosine similarity)
CREATE VECTOR INDEX soma_person_embedding IF NOT EXISTS 
FOR (n:Person) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_org_embedding IF NOT EXISTS 
FOR (n:Organization) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_place_embedding IF NOT EXISTS 
FOR (n:Place) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_concept_embedding IF NOT EXISTS 
FOR (n:Concept) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_object_embedding IF NOT EXISTS 
FOR (n:Object) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_tech_embedding IF NOT EXISTS 
FOR (n:Technology) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX soma_lang_embedding IF NOT EXISTS 
FOR (n:Language) ON n.embedding 
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
```

## Verify Indexes

```cypher
SHOW INDEXES;
```

All indexes should show status: `ONLINE`

## Dynamic Relationships

Relationships are created at runtime via APOC. No predefined schema needed.
Common types: `BELONGS_TO`, `WORKS_FOR`, `SUBMITS_TO`, `CONTROLS`, `RUNS_INSIDE`, `REFERENCES`, `DERIVED_FROM`
