import { useEffect, useState } from 'react';
import { ingressApi } from '@/lib/api/ingressApi';
import type { RawLakeStats } from '@/lib/api/types/ingress';
import { Database, RefreshCw } from 'lucide-react';

export function RawLakeStatusWidget() {
  const [stats, setStats] = useState<RawLakeStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await ingressApi.getRawLakeStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch raw_lake stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3"></div>
          <div className="space-y-2">
            <div className="h-4 bg-muted rounded"></div>
            <div className="h-4 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const successRate = stats.total_records > 0
    ? ((stats.processed / stats.total_records) * 100).toFixed(1)
    : '0';

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          Raw Lake Status
        </h3>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="p-2 hover:bg-muted rounded-md transition-colors"
          title="Refresh stats"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-background p-4 rounded-md border border-border">
          <p className="text-sm text-muted-foreground mb-1">Total Records</p>
          <p className="text-2xl font-bold">{stats.total_records.toLocaleString()}</p>
        </div>

        <div className="bg-background p-4 rounded-md border border-border">
          <p className="text-sm text-muted-foreground mb-1">Processed</p>
          <p className="text-2xl font-bold text-green-500">{stats.processed.toLocaleString()}</p>
        </div>

        <div className="bg-background p-4 rounded-md border border-border">
          <p className="text-sm text-muted-foreground mb-1">Pending</p>
          <p className="text-2xl font-bold text-yellow-500">{stats.pending.toLocaleString()}</p>
        </div>

        <div className="bg-background p-4 rounded-md border border-border">
          <p className="text-sm text-muted-foreground mb-1">Failed</p>
          <p className="text-2xl font-bold text-red-500">{stats.failed.toLocaleString()}</p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-border">
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Success Rate</span>
          <span className="font-semibold text-green-500">{successRate}%</span>
        </div>
        {stats.last_capture && (
          <div className="flex justify-between items-center text-sm mt-2">
            <span className="text-muted-foreground">Last Capture</span>
            <span className="font-mono text-xs">
              {new Date(stats.last_capture).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
