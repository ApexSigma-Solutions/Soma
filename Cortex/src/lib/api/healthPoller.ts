import { ApiClient, ApiHealth, omegaClient, ingestClient, memosClient } from '@/lib/api/client';
import { useAlertStore } from '@/lib/store/useAlertStore';

export type HealthUpdateCallback = (health: ApiHealth[]) => void;

// Track previous health to avoid duplicate alerts
const previousHealth: Map<string, boolean> = new Map();

export class HealthPoller {
  private clients: ApiClient[];
  private intervalId?: number;
  private callbacks: Set<HealthUpdateCallback> = new Set();
  private pollInterval: number;

  constructor(pollInterval = 10000) {
    this.pollInterval = pollInterval;
    this.clients = [omegaClient, ingestClient, memosClient];
  }

  async checkAllHealth(): Promise<ApiHealth[]> {
    const healthPromises = this.clients.map(client =>
      client.checkHealth()
    );

    const results = await Promise.all(healthPromises);
    
    // Check for status changes and trigger alerts
    results.forEach(health => {
      const wasHealthy = previousHealth.get(health.name);
      const isHealthy = health.healthy;
      
      // If service just went down (was healthy, now not)
      if (wasHealthy === true && !isHealthy) {
        useAlertStore.getState().addAlert({
          title: `${health.name} Service Unavailable`,
          message: health.error || 'Connection failed. Check service status.',
          severity: 'critical',
          service: health.name.toLowerCase() as 'omega' | 'ingest' | 'memos',
        });
      }
      
      previousHealth.set(health.name, isHealthy);
    });

    return results;
  }

  start() {
    if (this.intervalId) {
      return;
    }

    // Initial check
    this.checkAllHealth().then(health => {
      this.notifyCallbacks(health);
    });

    // Set up interval
    this.intervalId = window.setInterval(async () => {
      const health = await this.checkAllHealth();
      this.notifyCallbacks(health);
    }, this.pollInterval);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = undefined;
    }
  }

  async checkNow() {
      const health = await this.checkAllHealth();
      this.notifyCallbacks(health);
  }

  subscribe(callback: HealthUpdateCallback) {
    this.callbacks.add(callback);
    
    return () => {
      this.callbacks.delete(callback);
    };
  }

  private notifyCallbacks(health: ApiHealth[]) {
    this.callbacks.forEach(callback => callback(health));
  }
}

export const healthPoller = new HealthPoller();
