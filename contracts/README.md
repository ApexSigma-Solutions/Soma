# Soma Ecosystem API Contracts

This directory contains API contract definitions for all Soma services. Contracts define the expected behavior, endpoints, request/response formats, and dependencies for each service.

## Purpose

- **Service Integration**: Ensures services can communicate correctly
- **Validation**: Verifies services meet their defined contracts
- **Documentation**: Provides clear API specifications for developers
- **Testing**: Enables automated contract validation

## Contract Files

### ingress_contract.json
**Service**: InGress (Senses Layer)

Defines the lightweight data capture gateway endpoints:
- Health check endpoint
- Manual ingestion API
- Webhook endpoints (GitHub, Linear)
- System vitals telemetry

**Key Contracts**:
- `POST /api/v1/manual/ingest` - Manual signal ingestion
- `GET /health` - Service health check
- `GET /api/v1/system/vitals` - System telemetry

**Dependencies**: PostgreSQL (port 6000)

### ingest_contract.json
**Service**: InGest (Stomach Layer)

Defines the data processing and SimpleMem Stage 1 pipeline:
- Health check with comprehensive status
- Prometheus metrics endpoint
- Input/output schemas for data transformation

**Key Contracts**:
- Processing pipeline stages (Entropy Gate, Coreference, Temporal Anchoring)
- Redis Stream output format (soma_working_memory)
- Circuit breaker configuration

**Dependencies**: PostgreSQL, Redis (port 6380), Ollama (port 11434)

### omegakg_contract.json
**Service**: OmegaKG (Brain Layer)

Defines the graph persistence and vector embedding service:
- Capture server endpoints
- Worker specifications
- Neo4j node schemas

**Key Contracts**:
- Worker types (Embedding, Vector Index, Conversation)
- Neo4j node types (AtomicFact, ChatSession)
- Embedding configuration (BGE-M3, 1024 dimensions)

**Dependencies**: Neo4j (port 7687), Redis, PostgreSQL

### memos_contract.json
**Service**: memOS (Hands Layer)

Defines the MCP server for context retrieval:
- SSE endpoint for MCP communication
- MCP tool specifications
- Storage backends

**Key Contracts**:
- MCP Tools: `ingest_signal`, `query_brain`, `get_context`
- Storage backends: Neo4j (knowledge graph), LanceDB (vector search)

**Dependencies**: Neo4j, Redis, LanceDB, Ollama

## Contract Validation

Use the `validate_contracts.py` script to verify services meet their contracts:

```powershell
# Validate all services
python contracts/validate_contracts.py

# Validate specific services
python contracts/validate_contracts.py ingress ingest
```

The validator checks:
- Service is running on expected port
- Health endpoint responds with correct status code
- Response matches expected schema
- Required fields are present

## Contract Structure

Each contract follows this structure:

```json
{
  "contract_version": "x.y.z",
  "service": "ServiceName",
  "description": "Service description",
  "endpoints": {
    "endpoint_name": {
      "path": "/path",
      "method": "GET|POST|PUT|DELETE",
      "response": { ... }
    }
  },
  "input_schema": { ... },
  "output_schema": { ... },
  "dependencies": {
    "service_name": {
      "host": "hostname",
      "port": port_number,
      "required": boolean
    }
  },
  "health_check": {
    "endpoint": "/health",
    "expected_status_code": 200,
    "timeout_seconds": 5
  }
}
```

## Version Management

Contract versions follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes to API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, no API changes

When updating contracts:
1. Increment version number
2. Update all affected services
3. Run validation
4. Update documentation

## Integration with start_ecosystem.ps1

The `start_ecosystem.ps1` script uses contracts to:
1. Validate service health after startup
2. Verify inter-service communication
3. Ensure proper configuration
4. Fail fast if contracts don't match

## Best Practices

1. **Keep contracts up to date**: Update when API changes
2. **Validate before integration**: Use `validate_contracts.py` before connecting services
3. **Document breaking changes**: Update contract version and inform developers
4. **Test contract compliance**: Ensure services return expected responses
5. **Version control**: Track contract changes in git

## Troubleshooting

### Validation Fails

1. **Service not running**: Check service logs
2. **Port conflict**: Verify no other service using the port
3. **Schema mismatch**: Check service code matches contract
4. **Timeout**: Increase timeout in contract or check service health

### Contract Outdated

1. **Update contract**: Modify JSON file with new API spec
2. **Increment version**: Update `contract_version`
3. **Test validation**: Run `validate_contracts.py`
4. **Commit changes**: Include in git commit with version notes

## Related Documentation

- [STARTUP_GUIDE.md](../STARTUP_GUIDE.md) - Ecosystem startup instructions
- [AGENTS.md](../AGENTS.md) - Soma architecture and mental model
- Service READMEs in each service directory

## Support

For questions or issues with contracts:
1. Check service documentation
2. Review contract validation output
3. Check service logs for errors
4. Consult AGENTS.md for architecture details
