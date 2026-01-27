# CortexBridge AI Coding Agent Instructions

## Project Overview
CortexBridge is the **executive control plane** for the ApexSigma Omega Ecosystem. It's a React 19 + TypeScript + Vite 7 dashboard that monitors and controls three Python backend services: **Omega_KG** (port 8765), **InGest-LLM** (port 8766), and **memOS.MCP** (port 8768).

### Multi-Service Architecture
This is a **polyglot microservices workspace**:
- **Frontend**: CortexBridge (React + TypeScript + Vite) – this repo
- **Backend Services**: Python FastAPI microservices in sibling directories (`../OmegaKG`, `../InGest-LLM.as`, `../memOS.MCP`)
- **Databases**: PostgreSQL (pgvector), Neo4j, Redis run in Docker named volumes (see `../docker-compose.yml`)
- **Orchestration**: `Start-OmegaStack.py` launches all services with dependency-ordered startup and health checks

## Tech Stack & Toolchain
- **React 19** with TypeScript 5.9 (strict mode)
- **Vite 7** for dev server and build (`vite.config.ts`)
- **Vitest 4** for testing with `@testing-library/react` (`vitest.config.ts`)
- **Tailwind 4** + PostCSS with custom ApexSigma theme tokens in `src/index.css`
- **ESLint 9** flat config with TypeScript ESLint (`eslint.config.js`)
- **Zustand 5** for state management (no Redux/Context API)
- **Axios** for HTTP with interceptors for auth + health checks

## Architecture Patterns

### Routing & Auth
- **Hash-based routing** in `App.tsx` (`#omega`, `#ingest`, `#memos`, `#settings`)
- Auth protection: `useAuthStore` checks `isAuthenticated` before rendering dashboard
- Token stored via Zustand `persist` middleware (`auth-storage`); axios interceptor auto-attaches `Bearer` token
- **401 auto-logout** in `src/lib/api/client.ts` response interceptor (prevents loops on `/auth/token`)

### API Communication
- Three `ApiClient` instances in `src/lib/api/client.ts`: `omegaClient`, `ingestClient`, `memosClient`
- Typed API objects: `captureApi`, `ingestApi`, `memosApi` export methods (e.g., `captureApi.getRecent()`)
- Health polling via `src/lib/api/healthPoller.ts`: 10s interval, triggers alerts on service degradation
- **Env vars**: `VITE_API_OMEGA_URL`, `VITE_API_INGEST_URL`, `VITE_API_MEMOS_URL` (defaults in `.env.example`)

### State Management (Zustand)
- `useAuthStore`: auth state + login/logout/register
- `useSystemStore`: API health, theme (dark/light), sidebar collapse, system status (`online` | `degraded` | `offline`)
- `useToastStore`: imperative toasts via `toast.success()`, `toast.error()`, etc. (auto-dismiss after 4s)
- `useAlertStore`: critical alerts (service down) with severity levels

### Component Organization
```
src/components/
├── features/         # Feature-specific: capture/, ingest/, memos/
├── layout/          # DashboardLayout, Sidebar
├── pages/           # LoginPage, SettingsPage
├── ui/              # Reusable primitives: Button, Card, Badge, Input, Tabs, Toast, Skeleton
└── Dashboard.tsx    # Main dashboard view
```

### Lazy Loading & Suspense
- All feature routes lazy-loaded via `React.lazy` in `App.tsx`
- `<Suspense fallback={<ViewSkeleton />}>` wraps routes for loading states

## Development Workflows

### Starting the Full Stack
**Backend services** (Python FastAPI):
```bash
# From workspace root: Start databases + all Python services
python Start-OmegaStack.py
# Pre-flight checks: PostgreSQL (5432), Neo4j (7474/7687), pgvector extension
# Services start in order: OmegaKG → InGest-LLM → memOS.MCP
```

**Frontend** (this repo):
```bash
cd CortexBridge
npm run dev       # Start Vite dev server (localhost:5173)
```

### Database Access
- **PostgreSQL**: `localhost:5432` – `omega_user` / `omega_dev_password` / `omega_kg_stable` (Docker volume: `apexsigma.postgres.data`)
- **Neo4j**: `localhost:7474` (browser), `localhost:7687` (bolt) – `neo4j` / password set in `docker-compose.yml`
- **Redis**: Internal only (Docker volume: `apexsigma.redis.data`)
- Start databases only: `docker compose up -d` (from workspace root)

### Essential Commands
```bash
npm run dev       # Start Vite dev server (localhost:5173)
npm run build     # TypeScript check + Vite production build
npm run preview   # Preview production build
npm run test      # Run Vitest tests
npm run lint      # ESLint check
```

### Testing Conventions
- Tests use Vitest + `@testing-library/react` (setup in `src/test/setup.ts`)
- **lucide-react icons mocked** to avoid Proxy hangs (see `setup.ts`)
- Auto-cleanup after each test via `afterEach(cleanup)`

### Theme & Styling
- **ApexSigma Teal** (`#00BFA6`) is primary brand color
- Dark mode (default): deep navy backgrounds (`#020617`, `#0f172a`)
- Light mode: high-contrast white/slate (`#f8fafc`, `#020617`)
- Utility classes: `.text-glow`, `.border-glow`, `.glass-panel`, `.bg-grid-pattern`
- Tailwind config uses `@` alias (`@/components`, `@/lib`) resolved in `vite.config.ts`

## Critical Conventions

1. **No Redux/Context API**: Use Zustand for all global state
2. **Type safety**: All API responses typed (e.g., `CaptureResponse`, `IngestResponse`, `VectorHealth`)
3. **Error handling**: Axios interceptors handle 401s; use `try/catch` + `toast.error()` for user feedback
4. **Health checks**: Leverage `healthPoller` for real-time service monitoring (don't poll manually)
5. **Lazy imports**: Always use `React.lazy` for route components (keeps bundle small)
6. **CSS**: Use Tailwind classes; avoid inline styles. Custom tokens defined in `index.css` `:root`/`.dark`
7. **Microservices boundary**: CortexBridge is **frontend only** – backend logic lives in Python services (don't add FastAPI routes here)

## Integration Points & Data Flow

### Service Responsibilities
- **InGest-LLM** (Python, port 8766): **Ingestion gateway** – receives all raw data (text/file/repo), stores immediately in PostgreSQL data lake, enqueues for processing
- **OmegaKG** (Python, port 8765): **Knowledge authority** – validates/stores structured knowledge digests, manages Neo4j graph, generates embeddings (pgvector), RAG retrieval
- **memOS.MCP** (Python, port 8768): Working memory & context retrieval (native MCP mode; HTTP API mocked in `memosApi`)

### Data Pipeline (Designed Flow)
```
Raw Input → InGest-LLM (gateway)
          ↓ Immediate write to PostgreSQL data lake (100% retention)
          ↓ Worker processes raw → structured digests
          → OmegaKG (validation + storage)
          ↓ Embedding generation (pgvector)
          ↓ Graph mapping (Neo4j)
          → Ready for RAG retrieval
```

### Database Access Patterns
- **Shared databases**: PostgreSQL (pgvector data lake), Neo4j (knowledge graph), Redis (cache)
- **Write authority**: **OmegaKG should be** the single write authority for validated knowledge (⚠️ currently partial - see `ARCHITECTURE_VERIFICATION.md`)
- **InGest-LLM**: Writes raw data to data lake, reads for worker processing
- **Read-only**: CortexBridge, memOS.MCP consume via REST APIs (no direct DB writes)

### ⚠️ Known Architecture Gaps
See `ARCHITECTURE_VERIFICATION.md` for detailed analysis. Key issues:
1. InGest-LLM `/ingest/text` doesn't immediately persist raw data to data lake (data loss risk)
2. InGest-LLM worker writes directly to Neo4j, bypassing OmegaKG validation layer
3. Multiple services write to shared databases (consistency risk)
4. Terminal events processed inline without raw storage step

## Debugging & Cross-Service Issues
- Check backend logs in Python service directories (each service runs independently)
- Use browser DevTools Network tab to inspect API calls (look for 5xx errors from Python services)
- Health poller alerts (`useAlertStore`) trigger on backend service degradation
- Backend services NOT running: `Start-OmegaStack.py` handles orchestration (CortexBridge can't start them)

## Key Files for Reference
- `src/App.tsx` – Routing, auth guard, lazy loading
- `src/lib/api/client.ts` – API clients, health checks, typed endpoints
- `src/lib/api/healthPoller.ts` – 10s interval health poller
- `src/lib/store/` – Zustand stores (auth, system, toast, alert)
- `src/index.css` – ApexSigma theme tokens
- `vite.config.ts`, `vitest.config.ts` – Build/test config
