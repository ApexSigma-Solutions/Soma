# Soma Ecosystem Optimization Roadmap

> **Status**: Strategic Planning Document
> **Date**: January 25, 2026
> **Author**: ApexSigma Solutions

---

## Overview

This document outlines strategies for optimizing the Soma "Distributed Brain" architecture as it scales. The current hybrid architecture (Docker State Layer + Native Logic Layer) works well for development, but production deployment will benefit from:

1. **API Gateway** - Unified routing for all FastAPI services
2. **Service Discovery** - Dynamic service registration
3. **Unified Logging** - Centralized log aggregation

---

## 1. API Gateway Strategy

### Current Problem

Cortex (the frontend) must maintain multiple backend URLs:

- `http://localhost:8765` → OmegaKG (Brain)
- `http://localhost:8768` → memOS (Hands)
- `http://localhost:3000` → InGest/Dagster (Stomach)

This creates:

- Configuration fragility (hardcoded ports)
- CORS complexity (multiple origins)
- No centralized rate limiting or auth

### Recommended Solution: Traefik Reverse Proxy

**Why Traefik?**

- Docker-native with dynamic configuration
- Automatic HTTPS via Let's Encrypt
- Built-in dashboard for monitoring
- Path-based routing out of the box

**Proposed Configuration:**

```yaml
# docker-compose.yml addition

services:
  traefik:
    image: traefik:v3.0
    container_name: soma.gateway
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"  # Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - soma-network

  # Then label each service:
  omegakg:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.brain.rule=PathPrefix(`/api/brain`)"
      - "traefik.http.services.brain.loadbalancer.server.port=8765"

  memos:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hands.rule=PathPrefix(`/api/hands`)"
      - "traefik.http.services.hands.loadbalancer.server.port=8768"
```

**Result:**

- Cortex only needs: `https://soma.local/api/*`
- `/api/brain/*` → OmegaKG
- `/api/hands/*` → memOS
- `/api/stomach/*` → InGest

### Alternative: Custom FastAPI Router

If Traefik is overkill, a lightweight FastAPI gateway:

```python
# soma_gateway/main.py
from fastapi import FastAPI
import httpx

app = FastAPI(title="Soma Gateway")

SERVICES = {
    "brain": "http://localhost:8765",
    "hands": "http://localhost:8768",
    "stomach": "http://localhost:3000",
}

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(404, "Unknown service")
    
    async with httpx.AsyncClient() as client:
        url = f"{SERVICES[service]}/{path}"
        response = await client.request(
            method=request.method,
            url=url,
            headers=request.headers,
            content=await request.body(),
        )
        return Response(response.content, status_code=response.status_code)
```

---

## 2. Service Discovery

### Current Problem

Services discover each other via environment variables:

```ini
OMEGAKG_URL=http://localhost:8765
MEMOS_URL=http://localhost:8768
```

This breaks when:

- Ports change dynamically
- Services restart on different hosts
- Load balancing is needed

### Recommended Solution: Consul Service Mesh

**Why Consul?**

- HashiCorp ecosystem compatibility
- DNS-based discovery (simple)
- Health checks built-in
- Key/Value store for config

**Implementation Sketch:**

```yaml
# docker-compose.yml

services:
  consul:
    image: hashicorp/consul:1.17
    container_name: soma.consul
    ports:
      - "8500:8500"  # UI
      - "8600:8600/udp"  # DNS
    command: agent -server -bootstrap-expect=1 -ui -client=0.0.0.0
```

Services register themselves:

```python
# omega_kg/discovery.py
import consul

def register_service():
    c = consul.Consul()
    c.agent.service.register(
        name="omegakg",
        service_id="omegakg-1",
        address="localhost",
        port=8765,
        check=consul.Check.http("http://localhost:8765/health", interval="10s")
    )
```

**DNS-Based Discovery:**

```python
# Any service can find OmegaKG via:
import socket
address = socket.gethostbyname("omegakg.service.consul")
```

### Simpler Alternative: Docker DNS

If all services run in Docker, use Docker's built-in DNS:

```yaml
services:
  omegakg:
    container_name: brain
    networks:
      - soma-network

  memos:
    container_name: hands
    environment:
      - OMEGAKG_URL=http://brain:8765  # Docker DNS resolves this
    networks:
      - soma-network
```

---

## 3. Unified Logging Strategy

### Current Problem

Each service logs to its own terminal/file:

- `logs/omegakg_*.log`
- `logs/memos_*.log`
- `logs/ingest_*.log`

This makes debugging cross-service flows painful.

### Recommended Solution: Loki + Grafana Stack

**Why Loki?**

- Log aggregation designed for microservices
- Query language similar to PromQL
- Low resource usage compared to ELK
- Grafana integration for visualization

**Architecture:**

```
[OmegaKG] ──┐
[memOS]  ──────> [Promtail] ──> [Loki] ──> [Grafana]
[InGest] ──┘
```

**Docker Compose Addition:**

```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    container_name: soma.loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    container_name: soma.promtail
    volumes:
      - ./logs:/var/log/soma
      - ./promtail-config.yaml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:10.0.0
    container_name: soma.grafana
    ports:
      - "3001:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
```

### Simpler Alternative: Structured JSON Logging

Before adding infrastructure, standardize log format:

```python
# shared_logging.py
import structlog
import json

def configure_logging(service_name: str):
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    return structlog.get_logger().bind(service=service_name)
```

Output:

```json
{"timestamp": "2026-01-25T12:00:00Z", "level": "info", "service": "omegakg", "event": "capture_received", "user_id": "u123"}
```

Then aggregate with any tool (even `grep` across files).

---

## 4. Implementation Priority

| Phase | Component | Effort | Impact | Priority |
|-------|-----------|--------|--------|----------|
| 1 | Structured JSON Logging | Low | High | **Now** |
| 2 | Traefik API Gateway | Medium | High | Q1 2026 |
| 3 | Docker DNS (simple discovery) | Low | Medium | Q1 2026 |
| 4 | Loki/Grafana Stack | Medium | Medium | Q2 2026 |
| 5 | Consul Service Mesh | High | Medium | Q3 2026 |

---

## 5. Quick Wins

### Immediate Actions (This Week)

1. **Add correlation IDs** to all HTTP requests:

   ```python
   @app.middleware("http")
   async def add_correlation_id(request: Request, call_next):
       request.state.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
       response = await call_next(request)
       response.headers["X-Correlation-ID"] = request.state.correlation_id
       return response
   ```

2. **Standardize health endpoints** across all services:

   ```python
   GET /health -> { "status": "healthy", "service": "omegakg", "version": "0.1.0" }
   ```

3. **Create shared `soma-common` package** for:

   - Logging configuration
   - Auth utilities
   - Health check schemas

---

## Appendix: Current Architecture Reference

```markdown
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                         │
│   CortexBridge (React) @ :6001                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LOGIC LAYER (Native)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ OmegaKG     │  │ memOS.MCP   │  │ InGest (Dagster)    │  │
│  │ (Brain)     │  │ (Hands)     │  │ (Stomach)           │  │
│  │ :8765       │  │ :8768       │  │ :3000               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                   │               │
└─────────┼────────────────┼───────────────────┼───────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     STATE LAYER (Docker)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ PostgreSQL  │  │ Neo4j       │  │ Redis               │  │
│  │ :6000       │  │ :7474/:7687 │  │ :6380               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```
