// memOS API TypeScript types

export interface ScratchpadEntry {
  id: string;
  content: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

export interface WorkingMemory {
  [key: string]: string | number | boolean | object;
}

export interface ContextRetrievalRequest {
  query: string;
  limit?: number;
  threshold?: number;
  agent_id?: string;
}

export interface ContextRetrievalResult {
  query: string;
  working_memory: WorkingMemory;
  results_count: number;
  long_term_memory: {
    source: string;
    id: string;
    content: string;
    relevance: number;
    metadata: Record<string, unknown>;
    created_at: string;
  }[];
  sources: string[];
}

export interface MirmirConsultationRequest {
  plan: string;
  context?: string;
}

export interface MirmirConsultationResult {
  recommendation: string;
  confidence: number;
  reasoning: string;
  suggested_actions?: string[];
  status?: string;
  result?: string;
}

export interface MemoryPromotionRequest {
  session_id: string;
  key: string;
  significance?: 'low' | 'medium' | 'high';
}

export interface MemoryPromotionResult {
  status: 'promoted' | 'failed';
  memory_id?: string;
  message: string;
}
