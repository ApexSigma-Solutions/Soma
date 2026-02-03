import { useEffect, useState } from 'react';
import { ingressApi } from '@/lib/api/ingressApi';
import type { SystemVitals } from '@/lib/api/types/ingress';
import { Cpu, HardDrive, MemoryStick, RefreshCw } from 'lucide-react';

export function SystemVitalsWidget() {
  const [vitals, setVitals] = useState<SystemVitals | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVitals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ingressApi.getSystemVitals();
      setVitals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch vitals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVitals();
    // Poll every 30 seconds
    const interval = setInterval(fetchVitals, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (percent: number): string => {
    if (percent >= 90) return 'text-red-500';
    if (percent >= 75) return 'text-yellow-500';
    return 'text-green-500';
  };

  if (loading && !vitals) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3"></div>
          <div className="space-y-3">
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-destructive/50 rounded-lg p-6">
        <p className="text-destructive text-sm">Failed to load system vitals</p>
        <button
          onClick={fetchVitals}
          className="mt-2 text-sm text-primary hover:text-primary/80"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!vitals) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold">System Vitals</h3>
        <button
          onClick={fetchVitals}
          disabled={loading}
          className="p-2 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
          title="Refresh vitals"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-4">
        {/* CPU */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cpu className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">CPU Usage</p>
              <p className="text-xs text-muted-foreground">{vitals.cpu.cores} cores</p>
            </div>
          </div>
          <span className={`text-xl font-bold ${getStatusColor(vitals.cpu.percent)}`}>
            {vitals.cpu.percent.toFixed(1)}%
          </span>
        </div>

        {/* Memory */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MemoryStick className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Memory Usage</p>
              <p className="text-xs text-muted-foreground">
                {vitals.memory.available_mb.toFixed(0)} MB available
              </p>
            </div>
          </div>
          <span className={`text-xl font-bold ${getStatusColor(vitals.memory.percent)}`}>
            {vitals.memory.percent.toFixed(1)}%
          </span>
        </div>

        {/* Disk */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <HardDrive className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Disk Usage</p>
              <p className="text-xs text-muted-foreground">
                {vitals.disk.free_gb.toFixed(1)} GB free
              </p>
            </div>
          </div>
          <span className={`text-xl font-bold ${getStatusColor(vitals.disk.percent)}`}>
            {vitals.disk.percent.toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}
