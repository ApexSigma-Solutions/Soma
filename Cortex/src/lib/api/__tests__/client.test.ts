import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiClient } from '@/lib/api/client';
import axios from 'axios';

vi.mock('axios');

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient({
      name: 'Test',
      baseUrl: 'http://localhost:8000',
      port: 8000,
    });
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create an axios instance with correct config', () => {
      expect(axios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 5000,
      });
    });
  });

  describe('checkHealth', () => {
    it('should return healthy status on successful response', async () => {
      const mockResponse = { data: { status: 'ok' } };
      const mockAxiosInstance = {
        get: vi.fn().mockResolvedValue(mockResponse),
      };
      vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as any);

      const result = await client.checkHealth();

      expect(result).toEqual({
        name: 'Test',
        healthy: true,
        latency: expect.any(Number),
      });
    });

    it('should return unhealthy status on error', async () => {
      const mockAxiosInstance = {
        get: vi.fn().mockRejectedValue(new Error('Connection failed')),
      };
      vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as any);

      const result = await client.checkHealth();

      expect(result).toEqual({
        name: 'Test',
        healthy: false,
        error: 'Connection failed',
      });
    });
  });
});
