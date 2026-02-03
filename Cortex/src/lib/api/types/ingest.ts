// InGest API TypeScript types

export interface QueueStatus {
  pending: number;
  processing: number;
  completed: number;
  pending_count?: number;
  oldest_pending_age_seconds?: number;
  total_count?: number;
}

export interface PipelineStage {
  name: string;
  status: 'idle' | 'processing';
  last_processed?: string;
}

export interface PipelineStats {
  stages: PipelineStage[];
}

export interface CircuitBreakerStatus {
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  threshold: number;
  next_retry?: string;
}

export interface DigestStats {
  total_processed: number;
  success_count: number;
  failure_count: number;
  avg_processing_time_ms: number;
  daily_volume: { date: string; count: number }[];
}

export interface IngestionResult {
  ref: string;
  status: string;
}

export interface IngestResponse {
  ref: string;
  status: string;
  id?: string;
  message?: string;
}
