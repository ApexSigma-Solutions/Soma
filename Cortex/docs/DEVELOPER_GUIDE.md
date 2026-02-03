# Cortex Developer Guide

## Adding New Service Integrations

This guide explains how to add a new backend service integration to Cortex.

### Overview

To integrate a new service, you need to:
1. Create TypeScript types
2. Add API client methods
3. Create UI components
4. Add a page route
5. Update health poller
6. Add tests

### Step-by-Step Guide

#### 1. Create TypeScript Types

Create a new file in `src/lib/api/types/`:

```typescript
// src/lib/api/types/newservice.ts

export interface NewServiceStats {
  total_requests: number;
  active_connections: number;
  uptime_seconds: number;
}

export interface NewServiceRequest {
  param1: string;
  param2?: number;
}

export interface NewServiceResponse {
  id: string;
  status: 'success' | 'error';
  data: Record<string, unknown>;
}
```

#### 2. Add API Client Methods

Add to `src/lib/api/client.ts`:

```typescript
// Import types
import type {
  NewServiceStats,
  NewServiceRequest,
  NewServiceResponse,
} from './types/newservice';

// Create client instance
const newServiceClient = new ApiClient({
  name: 'NewService',
  baseUrl: import.meta.env.VITE_API_NEWSERVICE_URL || 'http://127.0.0.1:9000',
  port: 9000,
});

// Add to API_CONFIGS
export const API_CONFIGS: ApiConfig[] = [
  // ... existing configs
  {
    name: 'NewService',
    baseUrl: import.meta.env.VITE_API_NEWSERVICE_URL || 'http://127.0.0.1:9000',
    port: 9000,
  },
];

// Add API methods
export const newServiceApi = {
  getStats: async (): Promise<NewServiceStats> => {
    return newServiceClient.get<NewServiceStats>('/api/v1/stats');
  },

  processRequest: async (request: NewServiceRequest): Promise<NewServiceResponse> => {
    return newServiceClient.post<NewServiceResponse>('/api/v1/process', request);
  },
};
```

#### 3. Update Health Poller

Add the new client to `src/lib/api/healthPoller.ts`:

```typescript
import { newServiceClient } from '@/lib/api/client';

export class HealthPoller {
  constructor(pollInterval = 10000) {
    this.pollInterval = pollInterval;
    this.clients = [
      omegaClient,
      ingestClient,
      memosClient,
      ingressClient,
      newServiceClient, // Add here
    ];
  }
  // ... rest of class
}
```

#### 4. Create UI Components

Create a new folder `src/components/newservice/`:

```typescript
// src/components/newservice/StatsWidget.tsx
import { useEffect, useState } from 'react';
import { newServiceApi } from '@/lib/api/client';
import type { NewServiceStats } from '@/lib/api/types/newservice';

export function StatsWidget() {
  const [stats, setStats] = useState<NewServiceStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await newServiceApi.getStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3>NewService Stats</h3>
      <p>Total Requests: {stats.total_requests}</p>
      <p>Active Connections: {stats.active_connections}</p>
    </div>
  );
}
```

#### 5. Create Page Component

Create `src/pages/NewServicePage.tsx`:

```typescript
import { StatsWidget } from '@/components/newservice/StatsWidget';

export function NewServicePage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">NewService</h1>
        <p className="text-muted-foreground">
          Description of the new service
        </p>
      </div>
      <StatsWidget />
    </div>
  );
}
```

#### 6. Add Route

Update `src/App.tsx`:

```typescript
const NewServicePage = lazy(() => 
  import('@/pages/NewServicePage').then(module => ({ 
    default: module.NewServicePage 
  }))
);

// In renderContent switch statement:
case 'newservice':
  return <NewServicePage />;
```

#### 7. Add Environment Variable

Update `.env`:

```env
VITE_API_NEWSERVICE_URL=http://localhost:9000
```

#### 8. Add Tests

Create `src/components/newservice/__tests__/StatsWidget.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { StatsWidget } from '../StatsWidget';

vi.mock('@/lib/api/client');

describe('StatsWidget', () => {
  it('should display stats correctly', async () => {
    const mockStats = {
      total_requests: 1000,
      active_connections: 5,
      uptime_seconds: 3600,
    };

    vi.mocked(newServiceApi.getStats).mockResolvedValue(mockStats);

    render(<StatsWidget />);

    await waitFor(() => {
      expect(screen.getByText('1000')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });
});
```

### Best Practices

1. **Type Safety**: Always define TypeScript types for API requests/responses
2. **Error Handling**: Use try/catch and display user-friendly error messages
3. **Loading States**: Show loading indicators during async operations
4. **Polling**: Use appropriate intervals (10s for health, 30s for stats)
5. **Cleanup**: Always clear intervals in useEffect cleanup
6. **Testing**: Write unit tests for components and API methods
7. **Documentation**: Update README with new service information

### Common Patterns

#### Real-time Updates with SSE

```typescript
import { useSSEConnection } from '@/lib/api/sseConnection';

export function RealTimeWidget() {
  const [events, setEvents] = useState([]);

  useSSEConnection({
    url: 'http://localhost:9000/api/v1/events',
    onMessage: (message) => {
      setEvents((prev) => [message, ...prev].slice(0, 50));
    },
  });

  return <div>{/* Render events */}</div>;
}
```

#### Form with Validation

```typescript
export function RequestForm() {
  const [formData, setFormData] = useState({ param1: '' });
  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.param1) newErrors.param1 = 'Required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    await newServiceApi.processRequest(formData);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={formData.param1}
        onChange={(e) => setFormData({ ...formData, param1: e.target.value })}
      />
      {errors.param1 && <span className="text-red-500">{errors.param1}</span>}
    </form>
  );
}
```

### Troubleshooting

**Issue**: API calls failing with CORS errors
- **Solution**: Ensure backend has CORS configured for `http://localhost:5173`

**Issue**: Health checks not updating
- **Solution**: Verify client is added to HealthPoller constructor

**Issue**: Types not recognized
- **Solution**: Check that types are exported from `src/lib/api/types/index.ts`

### Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Vitest Testing](https://vitest.dev/)
- [Soma Architecture](../docs/SYSTEM_ARCHITECTURE_SUMMARY.md)
