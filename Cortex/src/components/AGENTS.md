# CORTEX COMPONENTS KNOWLEDGE

**Location:** Cortex/src/components/
**Purpose:** Feature-organized UI components

## STRUCTURE

```
components/
├── ingress/        # InGress (Senses) telemetry
├── ingest/         # InGest (Stomach) pipeline viz
├── omegakg/        # OmegaKG (Brain) graph browser
├── memos/          # memOS (Hands) MCP interface
├── telemetry/      # Cross-service metrics
├── visualization/  # Graph/chart primitives
├── ui/             # shadcn/ui design system
├── common/         # Shared (SystemHUD)
└── layout/         # Page wrappers (DashboardLayout)
```

## WHERE TO LOOK

| Feature | Components | Notes |
|---------|-----------|-------|
| Sensory signals | `ingress/` | Raw lake, webhooks, vitals |
| Metabolism viz | `ingest/` | Pipeline stages, circuit breaker, queue |
| Knowledge graph | `omegakg/` | Neo4j browser, atomic facts, semantic search |
| MCP tools | `memos/` | Scratchpad, context retrieval, Mirmir |
| Real-time streams | `telemetry/TelemetryStreamViewer.tsx` | SSE/EventSource |
| Graph viz | `visualization/` | D3/Recharts wrappers |
| Design system | `ui/` | Button, Card, Badge, Dialog, Toast |

## CONVENTIONS

**Component Structure:**
- One component per file
- Props interface above component
- Export named component (no default exports)
- Co-locate types/constants

**Naming:**
- `PascalCase.tsx` for components
- Props interface: `ComponentNameProps`
- Event handlers: `handleAction` (not `onAction` internal)

**Feature Organization:**
- `features/` = business domain groups
- Feature folders may contain multiple related components
- Shared UI primitives go in `ui/`

**State:**
- Local `useState` for component state
- Zustand stores for global (imported from `@/lib/store`)
- Props for parent-controlled state

**Styling:**
- Tailwind classes ONLY (no inline styles)
- Use `cn()` utility for conditional classes
- Custom tokens: `text-teal-500`, `bg-slate-900`, `border-slate-700`

**API Calls:**
- Import clients from `@/lib/api`
- Handle errors with try/catch + `toast.error()`
- Show loading state via `useState<boolean>`

## ANTI-PATTERNS

❌ **Default exports** - Use named exports
❌ **Inline styles** - Use Tailwind
❌ **Direct API URLs** - Import from `@/lib/api`
❌ **Global CSS classes** - Use Tailwind utilities
❌ **Prop drilling >3 levels** - Use Zustand store

## NOTES

**Feature Mapping:**
- `ingress/` → InGress service (port 8000)
- `ingest/` → InGest service (no HTTP, polls Postgres)
- `omegakg/` → OmegaKG capture server (port 8765)
- `memos/` → memOS MCP server (port 8768)

**Real-Time Patterns:**
- EventSource for SSE streams
- Polling fallback for legacy endpoints
- AbortController cleanup in `useEffect`

**Telemetry Components:**
- Live neural pulse stream visualization
- Service health indicators
- Meal trace E2E flow displays

**shadcn/ui in `ui/`:**
- Button, Card, Badge, Dialog, Toast
- Alert, Skeleton, Tabs, Input
- Composable primitives, NOT modified

---

*Parent: [../AGENTS.md](../AGENTS.md)*
