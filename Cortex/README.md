# Cortex

The **Executive Control Plane** for the Soma Biomorphic Knowledge Ecosystem.

Cortex is a React-based dashboard application that provides end-to-end integration with all Soma backend services, enabling full operational monitoring, control, and real-time telemetry visualization.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CORTEX (Port 5173)                       │
│                     React 19 + TypeScript + Vite                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   Dashboard  │ │   InGress    │ │   InGest     │            │
│  │   (Overview) │ │   (Senses)   │ │   (Stomach)  │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   OmegaKG    │ │    memOS     │ │  Telemetry   │            │
│  │   (Brain)    │ │   (Hands)    │ │  (Monitoring)│            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   InGress    │    │   InGest     │    │   OmegaKG    │
│   Port 8000  │    │   Port 8766  │    │   Port 8765  │
│  (Senses)    │    │  (Stomach)   │    │   (Brain)    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────┐
                    │    memOS     │
                    │   Port 8768  │
                    │   (Hands)    │
                    │  MCP Server  │
                    └──────────────┘
```

## ✨ Features

- **Modern Tech Stack**: React 19, TypeScript 5.9, Vite 7, Tailwind CSS, Recharts
- **Complete E2E Integration**: All 4 backend services (InGress, InGest, OmegaKG, memOS)
- **Real-time Monitoring**: Live health checks, SSE streams, and telemetry
- **Service Health Matrix**: Visual status of all services with latency metrics
- **Alert Notification System**: Critical alerts with severity levels
- **Meal Trace Visualization**: End-to-end signal flow tracking
- **Authentication**: JWT-ready login flow with protected routes
- **Ingestion Playground**: Multi-tab interface for Text and File ingestion
- **Semantic Search**: Hybrid vector + keyword search of knowledge graph
- **Mirmir Consultation**: AI-powered plan validation
- **Toast Notifications**: User feedback for all async actions
- **Performance**: Code-splitting with `React.lazy` for fast initial load
- **Loading Skeletons**: Smooth perceived performance during navigation
- **ApexSigma Theme**: Dark/Light mode with brand-aligned design tokens

## 📂 Project Structure

```
Cortex/
├── src/
│   ├── components/
│   │   ├── ingress/          # InGress (Senses) components
│   │   │   ├── ManualIngestForm.tsx
│   │   │   ├── SystemVitalsWidget.tsx
│   │   │   ├── TelemetryStreamViewer.tsx
│   │   │   ├── RawLakeStatusWidget.tsx
│   │   │   └── WebhookActivityLog.tsx
│   │   ├── ingest/           # InGest (Stomach) components
│   │   │   ├── IngestionPlayground.tsx
│   │   │   ├── QueueStatusDisplay.tsx
│   │   │   ├── PipelineStageVisualization.tsx
│   │   │   ├── CircuitBreakerIndicator.tsx
│   │   │   └── DigestStatsDashboard.tsx
│   │   ├── omegakg/          # OmegaKG (Brain) components
│   │   │   ├── SemanticSearchInterface.tsx
│   │   │   ├── AtomicFactBrowser.tsx
│   │   │   ├── KnowledgeCommitTracker.tsx
│   │   │   ├── CodexViolationDisplay.tsx
│   │   │   └── Neo4jGraphVisualization.tsx
│   │   ├── memos/            # memOS (Hands) components
│   │   │   ├── ScratchpadInterface.tsx
│   │   │   ├── WorkingMemoryViewer.tsx
│   │   │   ├── MemoryPromotionInterface.tsx
│   │   │   ├── MirmirConsultationUI.tsx
│   │   │   └── ContextRetrievalSearch.tsx
│   │   ├── telemetry/        # Telemetry components
│   │   │   ├── UnifiedPulseDisplay.tsx
│   │   │   ├── ServiceHealthMatrix.tsx
│   │   │   ├── AlertNotificationSystem.tsx
│   │   │   ├── HistoricalMetricsStorage.tsx
│   │   │   └── MealTraceVisualization.tsx
│   │   ├── ui/               # Shared UI components
│   │   │   ├── error-boundary.tsx
│   │   │   └── ...
│   │   └── features/         # Legacy feature components
│   ├── pages/                # Route pages
│   │   ├── InGressPage.tsx
│   │   ├── InGestPage.tsx
│   │   ├── OmegaKGPage.tsx
│   │   ├── MemosPage.tsx
│   │   ├── TelemetryPage.tsx
│   │   └── ...
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts     # API clients with retry logic
│   │   │   ├── sseConnection.ts
│   │   │   ├── healthPoller.ts
│   │   │   ├── ingressApi.ts
│   │   │   └── types/        # TypeScript types
│   │   │       ├── ingress.ts
│   │   │       ├── ingest.ts
│   │   │       ├── omegakg.ts
│   │   │       └── memos.ts
│   │   └── store/            # Zustand stores
│   │       ├── systemStore.ts
│   │       ├── useAuthStore.ts
│   │       ├── useToastStore.ts
│   │       └── useAlertStore.ts
│   ├── test/                 # Test setup
│   │   └── setup.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── e2e/                      # Playwright E2E tests
│   └── meal-trace.spec.ts
├── contracts/                # API contracts
│   └── cortex-api-contract.json
├── docs/                     # Documentation
│   └── DEVELOPER_GUIDE.md
└── package.json
```

## 🚀 Getting Started

### Prerequisites
- Node.js v20+
- npm

### Installation
```bash
cd CortexBridge
npm install
```

### Environment Variables
Create a `.env` file (copy from `.env.example`):
```env
# Backend Service URLs
VITE_API_OMEGA_URL=http://localhost:8765
VITE_API_INGEST_URL=http://localhost:8766
VITE_API_MEMOS_URL=http://localhost:8768
VITE_API_INGRESS_URL=http://localhost:8000

# API Security
VITE_API_KEY=sigma-dev-secret-key

# Optional: Observability
VITE_LANGFUSE_PUBLIC_KEY=
VITE_LANGFUSE_SECRET_KEY=
```

### Development
```bash
npm run dev
```
Access at `http://localhost:5173`. Default login: any email/password.

### Build
```bash
npm run build
npm run preview
```

### Testing
```bash
# Unit tests with Vitest
npm run test

# Unit tests with coverage
npm run test:coverage

# E2E tests with Playwright
npm run test:e2e

# Run specific test file
npm run test -- src/lib/api/__tests__/client.test.ts
```

## 🔌 API Integration

| Service | Port | API Object | Key Endpoints | Status |
|---------|------|------------|---------------|--------|
| InGress | 8000 | `ingressApi` | `/health`, `/api/v1/system/vitals`, `/api/v1/manual/ingest`, `/api/v1/telemetry/stream` | ✅ Integrated |
| InGest  | 8766 | `ingestApi` | `/health`, `/api/v1/ingest/text`, `/api/v1/ingest/file`, `/api/v1/queue/status` | ✅ Integrated |
| OmegaKG | 8765 | `omegaKgApi` | `/health`, `/api/v1/search`, `/api/v1/facts`, `/api/v1/commits` | ✅ Integrated |
| memOS   | 8768 | `memosApi` | `/health`, `/mcp/v1/tools/*` (MCP Server) | ✅ Integrated |

### API Client Features
- **Retry Logic**: Exponential backoff with 3 retries
- **Error Handling**: 401 triggers auto-logout, 503 triggers circuit breaker
- **Type Safety**: Full TypeScript types for all APIs
- **SSE Support**: Real-time event streaming
- **Health Polling**: Automatic 10s health checks

## 🎨 Theme

Configured in `index.css`. Based on ApexSigma Brand Guidelines.
- **Primary**: Boston Blue
- **Secondary**: Calypso
- **Backgrounds**: Deep Navy (dark) / Gray Nurse (light)

## 🧪 Testing Strategy

### Unit Tests (Vitest)
- **Location**: `src/**/__tests__/*.test.ts`
- **Coverage**: >80% for API clients and critical components
- **Run**: `npm run test:coverage`

### E2E Tests (Playwright)
- **Location**: `e2e/*.spec.ts`
- **Scenarios**: Meal trace flow, service health, error handling
- **Run**: `npm run test:e2e`

### Test Files
- `src/lib/api/__tests__/client.test.ts` - API client tests
- `src/components/ingress/__tests__/ManualIngestForm.test.tsx` - Component tests
- `src/components/telemetry/__tests__/ServiceHealthMatrix.test.tsx` - Health matrix tests
- `e2e/meal-trace.spec.ts` - Full E2E meal trace

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Environment Setup
1. Set all environment variables in production
2. Ensure all backend services are accessible
3. Configure reverse proxy (nginx/Caddy) if needed

### Docker Deployment
```dockerfile
# Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

### Static Hosting
Build outputs to `dist/` folder. Can be hosted on:
- Vercel
- Netlify
- GitHub Pages
- Any static file server

## 📚 Documentation

- [Developer Guide](./docs/DEVELOPER_GUIDE.md) - Adding new service integrations
- [API Contracts](../contracts/cortex-api-contract.json) - OpenAPI specification
- [Deployment Guide](./docs/DEPLOYMENT.md) - Production deployment steps
- [Architecture Overview](../docs/SYSTEM_ARCHITECTURE_SUMMARY.md) - Soma ecosystem

## 🤝 Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Run linting: `npm run lint`
5. Run type checking: `npm run type-check`

## 📖 License

See [LICENSE](LICENSE).
