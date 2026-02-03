CREATE VECTOR INDEX soma_person_embedding IF NOT EXISTS
FOR (n:Person)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_org_embedding IF NOT EXISTS
FOR (n:Organization)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_place_embedding IF NOT EXISTS
FOR (n:Place)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_concept_embedding IF NOT EXISTS
FOR (n:Concept)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_object_embedding IF NOT EXISTS
FOR (n:Object)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_tech_embedding IF NOT EXISTS
FOR (n:Technology)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};
CREATE VECTOR INDEX soma_lang_embedding IF NOT EXISTS
FOR (n:Language)
ON n.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};