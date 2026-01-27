# InGest-LLM.as

A microservice for ingesting data into the ApexSigma ecosystem. This service provides NLP-powered text parsing capabilities using Spacy Transformers and NLTK for extracting Knowledge Graphs from text.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Poetry 2.2.1+
- 4GB+ RAM (for Transformer model loading)

### Installation

```bash
# Install dependencies
poetry install

# ⚠️ MANDATORY: Download NLP models (required for Graph Parser)
python -m spacy download en_core_web_trf
python -m nltk.downloader punkt

# Start the server
poetry run uvicorn src.ingest_llm_as.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t ingest-llm-as .
docker run -p 8000:8000 ingest-llm-as
```

## 📖 Documentation

### Graph Parser API

The Graph Parser endpoint extracts Knowledge Graphs from text using dependency parsing:

**POST** `/graph/parse`

```json
{
    "text": "ApexSigma Solutions is integrating the new Design System. CortexBridge v4.0.2 utilizes React 18 and TailwindCSS. The module was deployed by SigmaDev11 in Cape Town.",
    "config": {}
}
```

**Response:**

```json
{
    "metadata": {
        "model": "en_core_web_trf",
        "sentences": 3,
        "entities": 7,
        "relations": 3
    },
    "nodes": [
        {"id": "ApexSigma Solutions", "type": "ORG"},
        {"id": "Design System", "type": "PRODUCT"},
        {"id": "CortexBridge v4.0.2", "type": "PRODUCT"},
        {"id": "React 18", "type": "PRODUCT"},
        {"id": "TailwindCSS", "type": "PRODUCT"},
        {"id": "SigmaDev11", "type": "PERSON"},
        {"id": "Cape Town", "type": "GPE"}
    ],
    "edges": [
        {"source": "ApexSigma Solutions", "relation": "integrating", "target": "Design System"},
        {"source": "CortexBridge v4.0.2", "relation": "utilizes", "target": "React 18"},
        {"source": "SigmaDev11", "relation": "deployed_in", "target": "Cape Town"}
    ]
}
```

### Health Check

**GET** `/graph/health`

```json
{
    "status": "ready",
    "model_loaded": true,
    "model_name": "en_core_web_trf"
}
```

### Omega Ingest API

See [API Reference](api_ingestion_endpoints.md) for Omega Ingest endpoints.

## 🛠️ Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=ingest_llm_as --cov-report=html

# Run specific test
poetry run pytest tests/test_document_parser.py -v
```

### Code Quality

```bash
# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Type check
poetry run mypy src/ingest_llm_as/

# Pre-commit hooks
poetry run pre-commit run --all-files
```

### Project Structure

```
src/ingest_llm_as/
├── api/
│   ├── __init__.py         # Router exports
│   ├── graph_parser.py     # Graph Parser endpoints
│   └── omega_ingest.py     # Omega Ingest endpoints
├── parsers/
│   ├── __init__.py         # Parser exports
│   └── document_parser.py  # DocumentParser class
├── main.py                 # FastAPI application
└── ...
```

## 📦 Dependencies

### Core Dependencies

- **FastAPI** - Web framework
- **Spacy** - NLP processing with Transformers
- **NLTK** - Sentence tokenization
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

### Optional Dependencies

- **Langfuse** - Observability
- **Neo4j** - Knowledge graph storage
- **OpenAI** - LLM integration

See [`pyproject.toml`](pyproject.toml) for full dependency list.

## 🔧 Configuration

Configure the service using environment variables (see [`.env.example`](.env.example)):

```env
# NLP Model Settings
SPACY_MODEL=en_core_web_trf

# Server Settings
HOST=0.0.0.0
PORT=8000

# Optional: Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

## 📚 Additional Resources

- [Service Status](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/00_History/STATUS.md) - Current development status
- [Deployment Guide](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/03_Implementation/deployment/infrastructure.md) - Production deployment
- [API Reference](api_ingestion_endpoints.md) - Complete API documentation

## 🏗️ Architecture

The service implements an extractive NLP approach for data provenance:

1. **Text Preprocessing** - Clean and normalize input text
2. **Sentence Tokenization** - Split into sentences using NLTK
3. **Dependency Parsing** - Use Spacy Transformers for high-fidelity parsing
4. **Entity Extraction** - Identify entities with Named Entity Recognition
5. **Relation Extraction** - Extract relationships via dependency traversal
6. **Knowledge Graph Output** - Return structured nodes and edges

This approach ensures all extracted information can be traced back to the original source text.
