# CortexBridge

The **Executive Control Plane** for the ApexSigma Omega Ecosystem.

CortexBridge is a React-based dashboard application that monitors and controls the three core services:
- **Omega_KG**: AI Conversation Capture & Knowledge Graph.
- **InGest-LLM**: Intelligent Data Ingestion Pipeline.
- **memos.MCP**: Working Memory & Context Retrieval (The "Second Brain").

## ✨ Features

- **Modern Tech Stack**: React 19, TypeScript, Vite 7, Tailwind 4.
- **Real-time Monitoring**: Live health checks and queue status for all services.
- **Authentication**: JWT-ready login flow with protected routes.
- **Ingestion Playground**: Multi-tab interface for Text, Repo, and File ingestion.
- **Semantic Search**: Query the knowledge graph directly from the UI.
- **Toast Notifications**: User feedback for all async actions.
- **Performance**: Code-splitting with `React.lazy` for fast initial load.
- **Loading Skeletons**: Smooth perceived performance during navigation.
- **ApexSigma Theme**: Dark/Light mode with brand-aligned design tokens.

## 📂 Project Structure

```
CortexBridge/
├── src/
│   ├── components/
│   │   ├── features/
│   │   │   ├── capture/      # CaptureControl, CaptureStatus, RecentCaptures
│   │   │   ├── ingest/       # IngestControl, IngestStatus, IngestPlayground
│   │   │   └── memos/        # MemosControl, MemosStatus, MemosSearch, MemosScratchpad
│   │   ├── layout/
│   │   │   └── DashboardLayout.tsx
│   │   ├── pages/
│   │   │   └── LoginPage.tsx
│   │   ├── ui/               # Button, Card, Badge, Input, Tabs, Toast, Skeleton
│   │   └── Dashboard.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts     # omegaClient, ingestClient, memosClient + typed APIs
│   │   │   └── healthPoller.ts
│   │   └── store/
│   │       ├── systemStore.ts   # Theme, sidebar state
│   │       ├── useAuthStore.ts  # Authentication state
│   │       └── useToastStore.ts # Toast notifications
│   ├── App.tsx               # Lazy routing, Suspense, ToastContainer
│   ├── main.tsx
│   └── index.css             # Tailwind & ApexSigma theme
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
VITE_API_OMEGA_URL=http://localhost:8765
VITE_API_INGEST_URL=http://localhost:8766
VITE_API_MEMOS_URL=http://localhost:8768
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
npm run test
```

## 🔌 API Integration

| Service | Port | API Object | Key Endpoints |
|---------|------|------------|---------------|
| Omega   | 8765 | `captureApi` | `/health`, `/capture`, `/capture/recent` |
| InGest  | 8766 | `ingestApi` | `/ingest/text`, `/ingest/file`, `/ingest/queue` |
| Memos   | 8768 | `memosApi` | `/memos/stats`, `/memos/search`, `/memos/scratch` |

## 🎨 Theme

Configured in `index.css`. Based on ApexSigma Brand Guidelines.
- **Primary**: Boston Blue
- **Secondary**: Calypso
- **Backgrounds**: Deep Navy (dark) / Gray Nurse (light)

## 📖 License

See [LICENSE](LICENSE).
