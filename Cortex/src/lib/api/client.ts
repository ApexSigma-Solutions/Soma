import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';

export interface ApiConfig {
  name: string;
  baseUrl: string;
  port: number;
}

export interface ApiHealth {
  name: string;
  healthy: boolean;
  lastChecked: Date;
  responseTime?: number;
  error?: string;
}

export const API_CONFIGS: ApiConfig[] = [
  {
    name: 'Omega',
    baseUrl: '/api/omega',
    port: 8765,
  },
  {
    name: 'InGest',
    baseUrl: '/api/ingest',
    port: 8766,
  },
  {
    name: 'Memos',
    baseUrl: '/api/memos',
    port: 8768,
  },
  {
    name: 'GraphParser',
    baseUrl: '/api/ingest',
    port: 8766,
  },
];

import { useAuthStore } from '@/lib/store/useAuthStore';
import { useToastStore } from '@/lib/store/useToastStore';

// ... (imports)

export class ApiClient {
  private config: ApiConfig;
  private client: AxiosInstance;

  constructor(config: ApiConfig) {
    this.config = config;
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
      
      const responseTime = performance.now() - startTime;

      return {
        name: this.config.name,
        healthy: true,
        lastChecked: new Date(),
        responseTime,
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
        lastChecked: new Date(),
        responseTime,
        error: errorMessage,
      };
    }
  }

  async get<T>(endpoint: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(endpoint, config);
    return response.data;
  }

  async post<T>(endpoint: string, data: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(endpoint, data, config);
    return response.data;
  }
}

// Create API client instances
export const omegaClient = new ApiClient(API_CONFIGS[0]);
export const ingestClient = new ApiClient(API_CONFIGS[1]);
export const memosClient = new ApiClient(API_CONFIGS[2]);
export const graphParserClient = new ApiClient(API_CONFIGS[3]);

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

export interface IngestResponse {
    ingestion_id: string;
    status: string;
    message: string;
    total_chunks?: number;
}

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

export interface QueueStatus {
    pending_count: number;
    processed_count: number;
    total_count: number;
    oldest_pending_age_seconds?: number;
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
    getServiceHealth: () => ingestClient.get<ServiceHealth>('/health'), // Basic health check
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
    consultMirmir: (query: string) => memosClient.post<MirmirResponse>('/mirmir/consult', { query }),
};