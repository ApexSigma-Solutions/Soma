import { useEffect, useState } from 'react';
import { ingestApi } from '@/lib/api/client';
import type { DigestStats } from '@/lib/api/types/ingest';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

export function DigestStatsDashboard() {
  const [stats, setStats] = useState<DigestStats | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await ingestApi.getDigestStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch digest stats:', error);
      }
    };

    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-64" />;

  const successRate = stats.total_processed > 0
    ? ((stats.success_count / stats.total_processed) * 100).toFixed(1)
    : '0';

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-primary" />
        Digest Statistics
      </h3>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-background p-4 rounded-md border border-border text-center">
          <p className="text-2xl font-bold">{stats.total_processed.toLocaleString()}</p>
          <p className="text-sm text-muted-foreground">Total Processed</p>
        </div>
        <div className="bg-background p-4 rounded-md border border-border text-center">
          <p className="text-2xl font-bold text-green-500">{successRate}%</p>
          <p className="text-sm text-muted-foreground">Success Rate</p>
        </div>
        <div className="bg-background p-4 rounded-md border border-border text-center">
          <p className="text-2xl font-bold">{stats.avg_processing_time_ms.toFixed(0)}ms</p>
          <p className="text-sm text-muted-foreground">Avg Time</p>
        </div>
        <div className="bg-background p-4 rounded-md border border-border text-center">
          <p className="text-2xl font-bold text-red-500">{stats.failure_count}</p>
          <p className="text-sm text-muted-foreground">Failures</p>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={stats.daily_volume}>
            <XAxis dataKey="date" stroke="currentColor" className="text-xs" />
            <YAxis stroke="currentColor" />
            <Tooltip
              contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
            />
            <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
