# InGest-LLM.as API Documentation
## Repository Ingestion and Integration Endpoints

**Version:** 0.1.0  
**Base URL:** `http://localhost:8000`  
**Task:** IG-20 - Formal API documentation for integration testing

---

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible during development.

---

## Core Endpoints

### Health Check

#### `GET /health`
Returns the health status of the InGest-LLM.as service.

**Response:**
```json
{
    "status": "healthy",
    "service": "InGest-LLM.as",
    "version": "0.1.0",
    "timestamp": "2025-08-23T10:30:00Z",
    "dependencies": {
        "memos": "available",
        "qdrant": "available",
        "lm_studio": "available"
    }
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is degraded

---

## Repository Ingestion

### Ingest Python Repository

#### `POST /ingest/python-repo`
Ingests a Python repository for analysis and storage in the knowledge management system.

**Request Body:**
```json
{
    "repository_source": "local_path" | "git_url",
    "source_path": "/path/to/repository",
    "metadata": {
        "source": "api",
        "content_type": "code",
        "project_name": "optional",
        "version": "optional"
    }
}
```

**Parameters:**
- `repository_source` (string, required): Source type for the repository
  - `"local_path"`: Local filesystem path
  - `"git_url"`: Git repository URL (future implementation)
- `source_path` (string, required): Path to the repository
- `metadata` (object, optional): Additional metadata for the ingestion
  - `source` (string): Origin of the request
  - `content_type` (string): Type of content being ingested
  - `project_name` (string): Name of the project
  - `version` (string): Version or commit hash

**Response:**
```json
{
    "status": "pending",
    "task_id": "uuid-string",
    "message": "Repository ingestion started",
    "estimated_completion": "2025-08-23T10:35:00Z"
}
```

**Status Codes:**
- `200 OK`: Ingestion task started successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Repository path not found
- `500 Internal Server Error`: Service error

**Example:**
```bash
curl -X POST "http://localhost:8000/ingest/python-repo" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_source": "local_path",
    "source_path": "/workspace/my-project",
    "metadata": {
      "source": "api",
      "content_type": "code",
      "project_name": "my-project"
    }
  }'
```

---

## Future Endpoints (Planned)

### Repository Analysis

#### `POST /api/v1/repository/analyze` *(Planned)*
Performs comprehensive analysis of a repository without full ingestion.

**Request Body:**
```json
{
    "repo_path": "/path/to/repository",
    "analysis_type": "basic" | "comprehensive",
    "include_dependencies": true,
    "file_types": ["py", "md", "txt"]
}
```

**Response:**
```json
{
    "repository_summary": {
        "name": "project-name",
        "languages": ["python"],
        "file_count": 42,
        "line_count": 1337
    },
    "file_analysis": [
        {
            "filename": "main.py",
            "type": "python",
            "size": 1024,
            "functions": ["main", "helper"]
        }
    ],
    "dependencies": {
        "requirements.txt": ["requests", "pytest"],
        "package.json": []
    }
}
```

### Document Ingestion

#### `POST /api/v1/documents/ingest` *(Planned)*
Ingests processed documents into target storage systems.

**Request Body:**
```json
{
    "repository_path": "/path/to/repository",
    "target": "memos" | "qdrant" | "both",
    "chunk_size": 1000,
    "enable_embeddings": true,
    "metadata_tags": ["tag1", "tag2"]
}
```

**Response:**
```json
{
    "status": "completed",
    "ingested_documents": 15,
    "target_storage": "memos",
    "embeddings_generated": true,
    "processing_time_ms": 2500
}
```

### Embedding Generation

#### `POST /api/v1/embeddings/generate` *(Planned)*
Generates embeddings for text content using configured models.

**Request Body:**
```json
{
    "content": "Text to generate embeddings for",
    "model": "nomic-embed-text-v1",
    "normalize": true
}
```

**Response:**
```json
{
    "embedding": [0.1, -0.2, 0.3, ...],
    "dimension": 768,
    "model": "nomic-embed-text-v1",
    "processing_time_ms": 150
}
```

---

## Integration with memOS.as

### Service Integration
InGest-LLM.as integrates with memOS.as (Memory Service) for persistent storage:

**memOS Connection:**
- **URL:** `http://memos-api:8090` (Docker) / `http://localhost:8091` (local)
- **Timeout:** 30 seconds
- **Health Check:** Verified during InGest-LLM.as startup

**Data Flow:**
1. Repository is analyzed by InGest-LLM.as
2. Content is chunked and processed
3. Documents are sent to memOS.as via REST API
4. memOS.as stores in tiered storage (PostgreSQL, Qdrant, Neo4j)
5. Embeddings are generated and stored for semantic search

### memOS Endpoints Used
- `POST /api/v1/memory/store` - Store processed documents
- `GET /api/v1/memory/search` - Verify storage and retrieval
- `GET /health` - Service health verification

---

## Error Handling

### Standard Error Response
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable error message",
        "details": "Additional error context",
        "timestamp": "2025-08-23T10:30:00Z"
    }
}
```

### Common Error Codes
- `INVALID_REPOSITORY_PATH`: Repository path does not exist
- `UNSUPPORTED_REPOSITORY_TYPE`: Repository type not supported
- `MEMOS_CONNECTION_FAILED`: Cannot connect to memOS.as
- `PROCESSING_FAILED`: Error during repository processing
- `STORAGE_FAILED`: Error storing processed data

---

## Configuration

### Service Settings
The service can be configured via environment variables:

```bash
# Service Configuration
INGEST_APP_NAME="InGest-LLM.as"
INGEST_DEBUG=false
INGEST_HOST="0.0.0.0"
INGEST_PORT=8000

# memOS Integration
INGEST_MEMOS_BASE_URL="http://memos-api:8090"
INGEST_MEMOS_TIMEOUT=30

# Processing Limits
INGEST_MAX_CONTENT_SIZE=1000000
INGEST_DEFAULT_CHUNK_SIZE=1000
INGEST_MAX_CHUNKS_PER_REQUEST=100

# LM Studio Integration
INGEST_LM_STUDIO_BASE_URL="http://host.docker.internal:1234/v1"
INGEST_LM_STUDIO_ENABLED=true

# Observability
LANGFUSE_PUBLIC_KEY="your-key"
LANGFUSE_SECRET_KEY="your-secret"
JAEGER_ENDPOINT="http://jaeger:14268/api/traces"
```

---

## Testing

### Integration Test Suite
Run the comprehensive integration test suite:

```bash
# Run all integration tests
pytest tests/test_repository_ingestion.py -v

# Run specific test categories
pytest tests/test_repository_ingestion.py::TestRepositoryIngestion::test_health_endpoints -v
pytest tests/test_repository_ingestion.py::TestRepositoryIngestion::test_ingest_python_repository -v

# Run with async support
pytest tests/test_repository_ingestion.py -v --asyncio-mode=auto
```

### Test Coverage
The integration tests cover:
- ✅ Health endpoint verification
- ✅ Python repository ingestion
- ✅ Error handling for invalid requests
- ✅ Concurrent request handling
- ✅ memOS.as integration (when available)
- 🔄 Document analysis (planned)
- 🔄 Embedding generation (planned)

---

## Monitoring and Observability

### Health Monitoring
- **Health Endpoint**: `/health`
- **Dependency Checks**: memOS.as, Qdrant, LM Studio connectivity
- **Service Metrics**: Processing time, success rates, error counts

### Distributed Tracing
- **Jaeger Integration**: Full request tracing across services
- **Langfuse Integration**: LLM-specific observability
- **Custom Spans**: Repository processing, embedding generation

### Metrics Collection
- Repository processing metrics
- memOS.as integration success rates
- Embedding generation performance
- Error rates and types

---

*Generated for Task IG-20 - Integration Test Suite and API Documentation*  
*Last Updated: August 23, 2025*