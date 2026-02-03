import { useEffect, useState } from 'react';
import { ingestApi } from '@/lib/api/client';
import type { CircuitBreakerStatus } from '@/lib/api/types/ingest';
import { Shield, AlertTriangle } from 'lucide-react';

export function CircuitBreakerIndicator() {
  const [status, setStatus] = useState<CircuitBreakerStatus | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await ingestApi.getCircuitBreakerStatus();
        setStatus(data);
      } catch (error) {
        console.error('Failed to fetch circuit breaker status:', error);
      }
    };

    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  const stateConfig = {
    closed: { color: 'text-green-500', bg: 'bg-green-500/20', label: 'Closed (Healthy)' },
    open: { color: 'text-red-500', bg: 'bg-red-500/20', label: 'Open (Circuit Tripped)' },
    half_open: { color: 'text-yellow-500', bg: 'bg-yellow-500/20', label: 'Half-Open (Testing)' },
  };

  const config = stateConfig[status.state];

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Shield className="h-5 w-5" />
        Circuit Breaker
      </h3>
      <div className={`p-4 rounded-md ${config.bg} flex items-center gap-3`}>
        <AlertTriangle className={`h-6 w-6 ${config.color}`} />
        <div className="flex-1">
          <p className={`font-semibold ${config.color}`}>{config.label}</p>
          <p className="text-sm text-foreground/80 mt-1">
            Failures: {status.failure_count} / {status.threshold}
          </p>
          {status.next_retry && (
            <p className="text-xs text-muted-foreground mt-1">
              Next retry: {new Date(status.next_retry).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
