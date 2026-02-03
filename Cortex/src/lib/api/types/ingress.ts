// InGress API TypeScript types and client

export interface SystemVitals {
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

export interface ManualIngestRequest {
  source?: string;
  event_type?: string;
  payload: Record<string, unknown>;
}

export interface IngestResponse {
  status: string;
  ref: string;
}

export interface TelemetryEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp?: string;
}

export interface RawLakeStats {
  total_records: number;
  processed: number;
  pending: number;
  failed: number;
  last_capture?: string;
}
