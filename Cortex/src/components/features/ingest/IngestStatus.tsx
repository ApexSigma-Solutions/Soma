import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ingestApi, IngestStats } from '@/lib/api/client';
import { Layers, Inbox, Zap, AlertTriangle } from 'lucide-react';

export function IngestStatus() {
  const [stats, setStats] = useState<IngestStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const data = await ingestApi.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch ingest stats', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return '0s';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  if (loading && !stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ingestion Hub</CardTitle>
        </CardHeader>
        <CardContent>Syncing pipeline metrics...</CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Pending Items */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pending Ingest</CardTitle>
          <Inbox className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.queue.pending_count || 0}</div>
          <div className="flex items-center gap-2 mt-1">
             <Badge variant={stats?.queue.pending_count === 0 ? 'success' : 'warning'} className="text-[10px] py-0">
               {stats?.queue.pending_count === 0 ? 'Clear' : 'Busy'}
             </Badge>
             <span className="text-xs text-muted-foreground">
               Wait: {formatDuration(stats?.queue.oldest_pending_age_seconds)}
             </span>
          </div>
        </CardContent>
      </Card>

      {/* Throughput */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Throughput (24h)</CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.throughput_24h || 0}</div>
          <p className="text-xs text-muted-foreground">
            Processed items
          </p>
        </CardContent>
      </Card>

      {/* Health / Error Rate */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pipeline Health</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.error_rate_24h.toFixed(1)}%</div>
          <p className="text-xs text-muted-foreground">
            Error rate (24h)
          </p>
        </CardContent>
      </Card>

      {/* Total Volume */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Historical Load</CardTitle>
          <Layers className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.queue.total_count || 0}</div>
          <p className="text-xs text-muted-foreground">
             Successful ingestions
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
