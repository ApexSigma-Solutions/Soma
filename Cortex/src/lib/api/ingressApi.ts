import { ingressClient } from '@/lib/api/client';
import type { 
  SystemVitals, 
  ManualIngestRequest, 
  IngestResponse, 
  RawLakeStats 
} from '@/lib/api/types/ingress';

const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key';

export const ingressApi = {
  /**
   * Get system vitals (CPU, Memory, Disk)
   */
  async getSystemVitals(): Promise<SystemVitals> {
    return ingressClient.get<SystemVitals>('/api/v1/system/vitals', {
      headers: {
        'x_api_key': API_KEY,
      },
    });
  },

  /**
   * Manually ingest a signal/event
   */
  async manualIngest(request: ManualIngestRequest): Promise<IngestResponse> {
    return ingressClient.post<IngestResponse>(
      '/api/v1/manual/ingest',
      request,
      {
        headers: {
          'x_api_key': API_KEY,
        },
      }
    );
  },

  /**
   * Get telemetry stream URL for SSE connection
   */
  getTelemetryStreamUrl(): string {
    const baseUrl = import.meta.env.VITE_API_INGRESS_URL || 'http://127.0.0.1:8000';
    return `${baseUrl}/api/v1/telemetry/stream`;
  },

  /**
   * Get raw_lake statistics (mock for now - implement when endpoint exists)
   */
  async getRawLakeStats(): Promise<RawLakeStats> {
    // TODO: Implement when InGress exposes this endpoint
    return {
      total_records: 0,
      processed: 0,
      pending: 0,
      failed: 0,
    };
  },
};
