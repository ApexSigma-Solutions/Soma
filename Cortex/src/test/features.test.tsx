import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CaptureControl } from '@/components/features/capture/CaptureControl';
import { IngestControl } from '@/components/features/ingest/IngestControl';
import { MemosControl } from '@/components/features/memos/MemosControl';

// Mock API clients to prevent actual network calls during tests
vi.mock('@/lib/api/client', () => ({
  omegaClient: {
    get: vi.fn().mockResolvedValue({
      status: 'healthy',
      vault_accessible: true,
      pending_count: 5,
      total_records: 100,
      worker_running: true
    }),
    post: vi.fn().mockResolvedValue({})
  },
  ingestClient: {
    get: vi.fn().mockResolvedValue({
      pending_count: 2,
      processed_count: 50,
      total_count: 52
    }),
    post: vi.fn().mockResolvedValue({})
  },
  memosClient: {
    get: vi.fn().mockImplementation((url) => {
      if (url.includes('stats')) {
        return Promise.resolve({
          total_memories: 200,
          by_tier: { semantic: 150, procedural: 50 },
          by_agent: { 'agent1': 10 },
          vector_dimension: 1536
        });
      }
      return Promise.resolve({ results: [] });
    }),
    post: vi.fn().mockResolvedValue({})
  },
  captureApi: {
      getVectorHealth: vi.fn().mockResolvedValue({
          pending_count: 5,
          total_records: 100,
          failed_count: 0,
          worker_running: true,
          status: 'healthy'
      }),
      getServiceHealth: vi.fn().mockResolvedValue({
          status: 'online',
          vault_accessible: true,
          postgres_connected: true
      }),
      getRecent: vi.fn().mockResolvedValue([]),
      manualCapture: vi.fn().mockResolvedValue({ success: true, message: 'Captured' }),
      controlService: vi.fn().mockResolvedValue({ status: 'ok' })
  }
}));

describe('Capture Control View', () => {
  it('renders status and manual form', async () => {
    render(<CaptureControl />);
    
    // Async wait for data to load
    await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Service Health/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /Vector Queue/i })).toBeInTheDocument();
    });
    
    // Static elements
    expect(screen.getByRole('heading', { name: /Manual Capture/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter text content here/i)).toBeInTheDocument();
  });
});

describe('InGest Control View', () => {
  it('renders queue status and playground', async () => {
    render(<IngestControl />);
    
    // Async wait for queue data
    await waitFor(() => {
         expect(screen.getByText(/Pending Queue/i)).toBeInTheDocument();
    });
    
    // Static elements
    expect(screen.getByRole('heading', { name: /Ingestion Playground/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Paste any text/i)).toBeInTheDocument();
  });
});

describe('Memos Control View', () => {
  it('renders stats and search', async () => {
    // Basic render check
    render(<MemosControl />);
    
    // Async wait for stats to load
    await waitFor(() => {
        expect(screen.getByRole('heading', { name: /Total Memories/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /Semantic/i })).toBeInTheDocument();
    });

    // Check Search interface presence
    expect(screen.getByRole('heading', { name: /Memory Search/i })).toBeInTheDocument();
    
    // We expect an input textbox
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});
