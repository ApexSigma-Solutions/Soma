# CORTEX KNOWLEDGE BASE

**Generated:** 2026-01-30
**Service:** Vision - Dashboard Hub

## OVERVIEW

React 19 + TypeScript + Vite dashboard for Soma organism telemetry. Real-time visualization of sensory signals, metabolism pipelines, and knowledge graph state. Zustand stores, Tailwind styling, Recharts viz.

## STRUCTURE

```
Cortex/src/
├── components/
│   ├── ingress/          # InGress telemetry widgets
│   ├── ingest/           # InGest pipeline viz
│   ├── omegakg/          # Neo4j graph browser
│   ├── memos/            # memOS MCP interface
│   ├── telemetry/        # Cross-service metrics
│   ├── visualization/    # Graph/chart components
│   ├── ui/               # shadcn/ui primitives
│   ├── common/           # Shared components (SystemHUD)
│   └── layout/           # DashboardLayout wrapper
├── pages/                # Route components
├── hooks/                # Custom React hooks
├── lib/                  # API clients, utils
└── types/                # TypeScript definitions
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Service API clients | `lib/api/` | Typed fetch wrappers |
| Real-time streams | `components/telemetry/` | EventSource/SSE |
| Neural telemetry UI | `components/memos/` | Pulse streams, Mirmir UI |
| Graph visualization | `components/omegakg/Neo4jGraphVisualization.tsx` | D3/Recharts |
| Meal trace UI | `components/telemetry/` | E2E flow visualization |
| State management | `lib/stores/` | Zustand (no Redux) |
| Theme/styling | `index.css` | Custom tokens, Tailwind config |
| Routing | `App.tsx` | React Router |

## CONVENTIONS

**TypeScript:**
- Strict mode (`noImplicitAny`, `strictNullChecks`)
- No `any` unless escape hatch critical
- Interfaces for object shapes
- `PascalCase` components/types, `camelCase` functions

**React Patterns:**
- Function components ONLY (no classes)
- Hooks for state/effects
- Component composition over inheritance
- Props destructuring in signatures

**State Management:**
- Zustand stores for global state
- Local `useState` for component-scoped
- NO Redux, NO Context API for globals
- Store pattern: `create()` + selectors

**Styling:**
- Tailwind CSS classes ONLY
- NO inline styles (`style={{}}`)
- Custom tokens in `index.css`
- shadcn/ui components in `components/ui/`

**API Calls:**
- Typed fetch wrappers in `lib/api/`
- Error handling via try/catch + toasts
- Loading states via `useState`
- AbortController for cleanup

**Naming:**
- Components: `PascalCase.tsx`
- Hooks: `useCamelCase.ts`
- Utils: `camelCase.ts`
- Types: `PascalCase` interfaces

## ANTI-PATTERNS

❌ **Default imports for named exports** - Use `import { X }` not `import X`
❌ **Inline styles** - Use Tailwind classes
❌ **Context API for global state** - Use Zustand
❌ **Class components** - Use function components
❌ **Any type** - Explicit types or `unknown`
❌ **Prop drilling** - Use Zustand for deeply nested state
❌ **Missing error boundaries** - Wrap risky components
❌ **Uncontrolled forms** - Use controlled inputs
❌ **Direct API URLs** - Use `lib/api/` clients

## COMMANDS

```bash
# Install
npm install

# Dev server (HMR)
npm run dev
# → http://localhost:5173

# Build production
npm run build

# Preview prod build
npm run preview

# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check

# Tests
npm test
npm test -- src/components/Button.test.tsx
```

## NOTES

**Service Integration:**
- InGress: `http://localhost:8000` (sensory signals)
- InGest: No direct API (polls Postgres)
- OmegaKG: `http://localhost:8765` (capture server)
- memOS: `http://localhost:8768` (MCP tools)

**Real-Time Features:**
- EventSource for SSE streams
- WebSocket planned (not implemented)
- Polling fallback for legacy endpoints

**Error Handling:**
- Toast notifications for user feedback
- Error boundaries for component crashes
- Retry logic in API clients

**Build Output:**
- `dist/` directory (gitignored)
- Static assets in `dist/assets/`
- HTML entry: `dist/index.html`

**Component Organization:**
- `features/` = business domain (capture, ingest, memos)
- `ui/` = shadcn primitives (button, card, dialog)
- `common/` = shared cross-domain (SystemHUD)
- `layout/` = page structure (DashboardLayout)

**Telemetry Dashboard:**
- Route: `/#cortex`
- Live neural stream visualization
- Service health indicators
- Meal trace E2E flows

---

*Service documentation: [Cortex/README.md](README.md)*
*Root context: [../AGENTS.md](../AGENTS.md)*
