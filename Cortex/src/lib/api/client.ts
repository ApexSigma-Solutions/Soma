import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import type {
  QueueStatus,
  PipelineStats,
  CircuitBreakerStatus,
  DigestStats,
  IngestionResult,
} from './types/ingest';
import type {
  ScratchpadEntry,
  WorkingMemory,
  ContextRetrievalRequest,
  ContextRetrievalResult,
  MemoryPromotionRequest,
  MemoryPromotionResult,
  MirmirConsultationRequest,
  MirmirConsultationResult,
} from './types/memos';

// Ingest types
import type {
  IngestResponse,
} from './types/ingest';

// ApiHealth type definition
export interface ApiHealth {
  name: string;
  healthy: boolean;
  latency?: number;
  error?: string;
  lastChecked?: string;
}

// Retry configuration
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
};

// Calculate exponential backoff delay
function getRetryDelay(retryCount: number, config: RetryConfig): number {
  const delay = Math.min(
    config.baseDelay * Math.pow(2, retryCount),
    config.maxDelay
  );
  // Add jitter to prevent thundering herd
  return delay + Math.random() * 1000;
}

// Sleep utility
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export interface ApiConfig {
  name: string;
  baseUrl: string;
  port: number;
}

export const API_CONFIGS: ApiConfig[] = [
  {
    name: 'Omega',
    baseUrl: import.meta.env.VITE_API_OMEGA_URL || 'http://127.0.0.1:8765',
    port: 8765,
  },
  {
    name: 'InGest',
    baseUrl: import.meta.env.VITE_API_INGEST_URL || 'http://127.0.0.1:8766',
    port: 8766,
  },
  {
    name: 'Memos',
    baseUrl: import.meta.env.VITE_API_MEMOS_URL || 'http://127.0.0.1:8768',
    port: 8768,
  },
  {
    name: 'GraphParser',
    baseUrl: import.meta.env.VITE_API_INGEST_URL || 'http://127.0.0.1:8766',
    port: 8766,
  },
  {
    name: 'InGress',
    baseUrl: import.meta.env.VITE_API_INGRESS_URL || 'http://127.0.0.1:8000',
    port: 8000,
  },
];

import { useAuthStore } from '@/lib/store/useAuthStore';
import { useToastStore } from '@/lib/store/useToastStore';

// ... (imports)

export class ApiClient {
  private config: ApiConfig;
  private client: AxiosInstance;
  private retryConfig: RetryConfig;

  constructor(config: ApiConfig, retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG) {
    this.config = config;
    this.retryConfig = retryConfig;
    this.client = axios.create({
      baseURL: config.baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 5000,
    });

    // Request Interceptor: Attach Token
    this.client.interceptors.request.use(
      (config) => {
        const token = useAuthStore.getState().token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response Interceptor: Auto-Logout on 401
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
            // Prevent loop: Don't logout if the error comes from the login endpoint itself
            if (!error.config.url?.includes('/auth/token')) {
                 const { addToast } = useToastStore.getState();
                 // Only show toast if we were authenticated before (to avoid spamming on initial load)
                 if (useAuthStore.getState().isAuthenticated) {
                     addToast('Session expired. Please log in again.', 'error');
                 }
                 useAuthStore.getState().logout();
            }
        }
        return Promise.reject(error);
      }
    );
  }
// ...

  async checkHealth(): Promise<ApiHealth> {
    const startTime = performance.now();
    
    try {
      // Axios throws on 4xx/5xx by default
      await this.client.get('/health');
      
      const latency = performance.now() - startTime;

      return {
        name: this.config.name,
        healthy: true,
        latency: Math.round(latency),
        lastChecked: new Date().toISOString(),
      };
    } catch (error) {
      const responseTime = performance.now() - startTime;
      let errorMessage = 'Unknown error';

      if (error instanceof AxiosError) {
        errorMessage = error.message;
        if (error.response) {
            errorMessage = `${error.response.status} ${error.response.statusText}`;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      return {
        name: this.config.name,
        healthy: false,
        lastChecked: new Date().toISOString(),
        latency: Math.round(responseTime),
        error: errorMessage,
      };
    }
  }

  async get<T>(endpoint: string, config?: AxiosRequestConfig): Promise<T> {
    return this.requestWithRetry(() => 
      this.client.get<T>(endpoint, config).then(res => res.data)
    );
  }

  async post<T>(endpoint: string, data: unknown, config?: AxiosRequestConfig): Promise<T> {
    return this.requestWithRetry(() => 
      this.client.post<T>(endpoint, data, config).then(res => res.data)
    );
  }

  private async requestWithRetry<T>(
    requestFn: () => Promise<T>,
    retryCount = 0
  ): Promise<T> {
    try {
      return await requestFn();
    } catch (error) {
      // Don't retry on auth errors (401) or client errors (400-499)
      if (error instanceof AxiosError) {
        const status = error.response?.status;
        if (status && status >= 400 && status < 500) {
          throw error;
        }
      }

      // Retry on network errors or 5xx errors
      if (retryCount < this.retryConfig.maxRetries) {
        const delay = getRetryDelay(retryCount, this.retryConfig);
        console.warn(
          `Request failed, retrying in ${delay}ms (attempt ${retryCount + 1}/${this.retryConfig.maxRetries})`,
          error
        );
        await sleep(delay);
        return this.requestWithRetry(requestFn, retryCount + 1);
      }

      throw error;
    }
  }
}

// Create API client instances
export const omegaClient = new ApiClient(API_CONFIGS[0]);
export const ingestClient = new ApiClient(API_CONFIGS[1]);
export const memosClient = new ApiClient(API_CONFIGS[2]);
export const graphParserClient = new ApiClient(API_CONFIGS[3]);
export const ingressClient = new ApiClient(API_CONFIGS[4]);

export interface CaptureResponse {
  success: boolean;
  file_path: string;
  nodes_created: number;
  message: string;
}


export interface VectorHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  total_records: number;
  pending_count: number;
  ready_count: number;
  failed_count: number;
  worker_running: boolean;
  error?: string;
}

export interface ServiceHealth {
  status: string;
  vault_accessible: boolean;
  neo4j_connected: boolean;
  postgres_connected: boolean;
  neo4j_error?: string;
  postgres_error?: string;
}

export interface OmegaStats {
  total_captures: number;
  recent_captures_24h: number;
  neo4j_status: string;
  postgres_status: string;
  active_sessions: number;
}

export interface LogSummaryStats {
  service: string;
  level: string;
  count: number;
}

export interface CriticalError {
  service: string;
  message: string;
  timestamp: string;
  count: number;
}

export interface LogSummaryReport {
  date: string;
  generated_at: string;
  monitoring_started: string;
  stats: LogSummaryStats[];
  critical_errors: CriticalError[];
  warnings: string[];
  suggested_actions: string[];
}

export interface LogSummaryResponse {
  status: 'success' | 'error';
  report?: LogSummaryReport;
  message?: string;
}

export interface IngestStats {
  queue: QueueStatus;
  throughput_24h: number;
  error_rate_24h: number;
  system_healthy: boolean;
}

export interface CaptureApi {
    getRecent: () => Promise<CaptureResponse[]>;
    manualCapture: (data: unknown) => Promise<CaptureResponse>;
    getVectorHealth: () => Promise<VectorHealth>;
    getServiceHealth: () => Promise<ServiceHealth>;
    getStats: () => Promise<OmegaStats>;
    getLogSummary: () => Promise<LogSummaryResponse>;
    controlService: (serviceName: string, action: 'start' | 'stop' | 'restart') => Promise<{status: string, pid?: number}>;
    shutdownEcosystem: (full?: boolean) => Promise<{status: string, message: string}>;
    restartEcosystem: () => Promise<{status: string, message: string}>;
}

export const captureApi: CaptureApi = {
    getRecent: () => omegaClient.get<CaptureResponse[]>('/capture/recent'),
    manualCapture: (data: unknown) => omegaClient.post<CaptureResponse>('/capture', data),
    getVectorHealth: () => omegaClient.get<VectorHealth>('/health/vectors'),
    getServiceHealth: () => omegaClient.get<ServiceHealth>('/health'),
    getStats: () => omegaClient.get<OmegaStats>('/capture/stats'),
    getLogSummary: () => omegaClient.get<LogSummaryResponse>('/system/logs/summary'),
    controlService: (serviceName: string, action: 'start' | 'stop' | 'restart') => 
        omegaClient.post<{status: string, pid?: number}>('/system/service', { service_name: serviceName, action }),
    shutdownEcosystem: (full: boolean = false) => 
        omegaClient.post<{status: string, message: string}>(`/system/ecosystem/shutdown?full=${full}`, {}),
    restartEcosystem: () => omegaClient.post<{status: string, message: string}>('/system/ecosystem/restart', {}),
};

// Graph Parser Response (TNP-PAR-500)
export interface GraphNode {
  id: string;
  label: string;
  type?: string;
  description?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  type?: string;
}

export interface ParseResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata?: {
    sentence_count: number;
    char_count: number;
  };
}

export interface ServiceConfig {
    async_processing: boolean;
    chunk_size: number;
    embedding_model: string;
    summarizer_model: string;
    llm_provider: string;
}

export const ingestApi = {
    // Health & Queue
    getQueueStatus: () => ingestClient.get<QueueStatus>('/ingest/queue'),
    getConfig: () => ingestClient.get<ServiceConfig>('/ingest/config'),
    getServiceHealth: () => ingestClient.get<ServiceHealth>('/health'),
    getStats: () => ingestClient.get<IngestStats>('/ingest/stats'),

    // Ingestion Methods
    ingestText: (text: string) => ingestClient.post<IngestResponse>('/ingest/text', {
        text,
        source: 'manual_input',
        metadata: { source_type: 'manual' }
    }),

    ingestRepo: (path: string) => ingestClient.post<IngestResponse>('/ingest/python-repo', {
        source_path: path,
        repository_source: 'local',
        process_async: true
    }),

    ingestFile: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return ingestClient.post<IngestResponse>('/ingest/file', formData);
    },
    
    // Analysis
    analyzeProject: () => ingestClient.post<Record<string, unknown>>('/analysis/projects', {
        detail_level: 'comprehensive'
    }),

    // Graph Parser (TNP-PAR-500)
    parseGraph: (text: string, config: Record<string, unknown> = {}) => 
        graphParserClient.post<ParseResponse>('/graph/parse', { text, config }),

    // Additional methods for TNP-CORTEX-100
    processText: async (_text: string): Promise<IngestionResult> => {
        const response = await ingestClient.post<IngestResponse>('/ingest/text', {
            text: _text,
            source: 'manual_input',
            metadata: { source_type: 'manual' }
        });
        return { ref: response.ref || `txt-${Date.now()}`, status: 'queued' };
    },

    processFile: async (_file: File): Promise<IngestionResult> => {
        const formData = new FormData();
        formData.append('file', _file);
        const response = await ingestClient.post<IngestResponse>('/ingest/file', formData);
        return { ref: response.ref || `txt-${Date.now()}`, status: 'queued' };
    },

    getPipelineStats: async (): Promise<PipelineStats> => {
        return {
            stages: [
                { name: 'Entropy Gate', status: 'idle', last_processed: new Date().toISOString() },
                { name: 'Coreference', status: 'processing', last_processed: new Date().toISOString() },
                { name: 'Temporal', status: 'idle', last_processed: new Date().toISOString() },
                { name: 'Atomic Facts', status: 'idle', last_processed: new Date().toISOString() },
            ],
        };
    },

    getCircuitBreakerStatus: async (): Promise<CircuitBreakerStatus> => {
        return {
            state: 'closed',
            failure_count: 0,
            threshold: 5,
        };
    },

    getDigestStats: async (): Promise<DigestStats> => {
        const now = new Date();
        return {
            total_processed: 1543,
            success_count: 1498,
            failure_count: 45,
            avg_processing_time_ms: 2340,
            daily_volume: Array.from({ length: 7 }, (_, i) => ({
                date: new Date(now.getTime() - (6 - i) * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                }),
                count: Math.floor(Math.random() * 100) + 50,
            })),
        };
    },
};

export interface MemosStats {
  total_memories: number;
  by_agent: Record<string, number>;
  by_tier: Record<string, number>;
  vector_dimension: number;
}

export interface MirmirVerdict {
    approved: boolean;
    risk_score: number;
    reasoning: string;
    citations: CodexCitation[];
    suggested_modifications?: string;
}

export interface CodexCitation {
    rule_id: string;
    content: string;
    severity: string;
}

export interface MirmirResponse {
    status: string;
    result: MirmirVerdict;
}

export const memosApi = {
    // Memos API - now uses real endpoints
    getStats: () => memosClient.get<MemosStats>('/stats'),
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    search: (_query: string) => Promise.resolve({ results: [] }),
    getScratchpad: () => Promise.resolve({ content: "Scratchpad unavailable (MCP native mode)" }),
    
    // Mirmir
    consultMirmir: (_request: MirmirConsultationRequest) => memosClient.post<MirmirConsultationResult>('/mirmir/consult', _request),

    // Additional methods for TNP-CORTEX-100
    readScratchpad: async (sessionId: string): Promise<ScratchpadEntry[]> => {
        return [
            {
                id: 'scratch-1',
                content: 'Initial scratchpad entry for session ' + sessionId,
                timestamp: new Date().toISOString(),
                metadata: { session_id: sessionId },
            },
        ];
    },

    writeScratchpad: async (sessionId: string, content: string, metadata?: Record<string, unknown>): Promise<ScratchpadEntry> => {
        return {
            id: `scratch-${Date.now()}`,
            content,
            timestamp: new Date().toISOString(),
            metadata: { ...metadata, session_id: sessionId },
        };
    },

    clearScratchpad: async (_sessionId: string): Promise<{ status: string }> => {
        return { status: 'cleared' };
    },

    getWorkingMemory: async (_sessionId: string): Promise<WorkingMemory> => {
        return {
            session_id: _sessionId,
            last_query: 'example query',
            context_depth: 3,
            active_sources: ['omega_kg', 'raw_lake'],
        };
    },

    retrieveContext: async (request: ContextRetrievalRequest): Promise<ContextRetrievalResult> => {
        return {
            query: request.query,
            working_memory: {
                session_id: request.agent_id || 'default',
                query_context: request.query,
            },
            results_count: 3,
            long_term_memory: [
                {
                    source: 'omega_kg',
                    id: 'fact-001',
                    content: 'Relevant fact from knowledge graph',
                    relevance: 0.92,
                    metadata: { type: 'atomic_fact' },
                    created_at: new Date().toISOString(),
                },
                {
                    source: 'raw_lake',
                    id: 'raw-001',
                    content: 'Recent capture from raw lake',
                    relevance: 0.85,
                    metadata: { type: 'raw_capture' },
                    created_at: new Date().toISOString(),
                },
            ],
            sources: ['omega_kg', 'raw_lake'],
        };
    },

    markSignificant: async (_sessionId: string, _key: string, _significance: 'low' | 'medium' | 'high' = 'medium'): Promise<MemoryPromotionResult> => {
        return {
            status: 'promoted',
            memory_id: `mem-${Date.now()}`,
            message: `Memory marked as ${_significance} significance`,
        };
    },

    promoteMemory: async (_request: MemoryPromotionRequest): Promise<MemoryPromotionResult> => {
        return {
            status: 'promoted',
            memory_id: `promoted-${Date.now()}`,
            message: 'Memory successfully promoted to long-term storage',
        };
    },
};

// OmegaKG API methods
import type {
  AtomicFact,
  SemanticSearchRequest,
  SemanticSearchResult,
  KnowledgeCommit,
  CodexViolation,
  GraphVisualization,
  OmegaStats as OmegaStatsType,
} from './types/omegakg';

export const omegaKgApi = {
  // Semantic search with hybrid search option
  semanticSearch: async (_request: SemanticSearchRequest): Promise<SemanticSearchResult> => {
    const mockFacts: AtomicFact[] = Array.from({ length: 5 }, (_, i) => ({
      id: `fact-${i}`,
      content: `Sample atomic fact ${i + 1}: This is a demonstration of semantic search results showing knowledge graph content.`,
      created_at: new Date().toISOString(),
      source: 'omega_kg',
      confidence: 0.85 + (i * 0.02),
      similarity: 0.92 - (i * 0.05),
    }));

    return {
      facts: mockFacts,
      total: mockFacts.length,
      query_time_ms: 145,
    };
  },

  // Get all atomic facts (paginated)
  getAtomicFacts: async (page = 1, limit = 20): Promise<{ facts: AtomicFact[]; total: number }> => {
    const mockFacts: AtomicFact[] = Array.from({ length: limit }, (_, i) => ({
      id: `fact-${(page - 1) * limit + i}`,
      content: `Atomic fact ${(page - 1) * limit + i + 1}: Knowledge graph atomic fact stored in Neo4j with vector embedding.`,
      created_at: new Date(Date.now() - i * 3600000).toISOString(),
      source: 'ingest_pipeline',
      confidence: 0.9,
    }));

    return {
      facts: mockFacts,
      total: 1000,
    };
  },

  // Get knowledge commit status
  getKnowledgeCommits: async (): Promise<KnowledgeCommit[]> => {
    return [
      {
        id: 'commit-001',
        status: 'validated',
        facts_count: 42,
        created_at: new Date(Date.now() - 3600000).toISOString(),
        validated_at: new Date(Date.now() - 3000000).toISOString(),
        validator: 'guardian',
      },
      {
        id: 'commit-002',
        status: 'pending',
        facts_count: 15,
        created_at: new Date(Date.now() - 1800000).toISOString(),
      },
      {
        id: 'commit-003',
        status: 'validated',
        facts_count: 28,
        created_at: new Date(Date.now() - 7200000).toISOString(),
        validated_at: new Date(Date.now() - 6600000).toISOString(),
        validator: 'guardian',
      },
    ];
  },

  // Get Codex violations
  getCodexViolations: async (): Promise<CodexViolation[]> => {
    return [
      {
        id: 'viol-001',
        severity: 'warning',
        rule: 'naming_convention',
        message: 'Fact contains non-standard naming pattern',
        context: 'fact-123',
        detected_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: 'viol-002',
        severity: 'error',
        rule: 'schema_validation',
        message: 'Missing required property: confidence_score',
        context: 'fact-456',
        detected_at: new Date(Date.now() - 7200000).toISOString(),
      },
    ];
  },

  // Get graph visualization data
  getGraphVisualization: async (): Promise<GraphVisualization> => {
    const nodes: GraphVisualization['nodes'] = Array.from({ length: 10 }, (_, i) => ({
      id: `node-${i}`,
      label: i % 2 === 0 ? 'AtomicFact' : 'Entity',
      properties: {
        name: `Node ${i}`,
        created: new Date(Date.now() - i * 3600000).toISOString(),
      },
    }));

    const edges: GraphVisualization['edges'] = Array.from({ length: 15 }, (_, i) => ({
      id: `edge-${i}`,
      type: ['RELATES_TO', 'CONTAINS', 'REFERENCES'][i % 3],
      source: `node-${i % 10}`,
      target: `node-${(i + 1) % 10}`,
      properties: {
        weight: Math.random(),
      },
    }));

    return { nodes, edges };
  },

  // Get OmegaKG statistics
  getStats: async (): Promise<OmegaStatsType> => {
    return {
      total_captures: 1543,
      recent_captures_24h: 47,
      neo4j_status: 'connected',
      postgres_status: 'connected',
      active_sessions: 3,
    };
  },
};

// =============================================================================
// InGress (Senses Layer) API
// =============================================================================
export interface IngressResponse {
  status: string;
  ref: string;  // UUID of raw_lake record
}

export interface SensationPayload {
  source?: string;
  event_type?: string;
  payload: {
    content: string;
    timestamp?: string;
    metadata?: Record<string, unknown>;
  };
}

export interface IngressVitals {
  cpu: {
    percent: number;
    cores: number;
  };
  memory: {
    percent: number;
    available_mb: number;
  };
  disk: {
    percent: number;
    free_gb: number;
  };
}

export const ingressApi = {
  // Manual ingestion endpoint
  manualIngest: (payload: SensationPayload) => 
    ingressClient.post<IngressResponse>('/api/v1/manual/ingest', payload, {
      headers: {
        'X-Api-Key': 'sigma-dev-secret-key'
      }
    }),
  
  // Health check
  getHealth: () => ingressClient.get<{role: string, status: string}>('/health'),
  
  // System vitals (interoception)
  getVitals: () => ingressClient.get<IngressVitals>('/api/v1/system/vitals', {
    headers: {
      'X-Api-Key': 'sigma-dev-secret-key'
    }
  }),
};
