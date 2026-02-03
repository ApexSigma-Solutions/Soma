import { useEffect, useState } from 'react';
import { ingestApi } from '@/lib/api/client';
import type { QueueStatus } from '@/lib/api/types/ingest';
import { Clock, CheckCircle, Loader2 } from 'lucide-react';

export function QueueStatusDisplay() {
  const [status, setStatus] = useState<QueueStatus | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await ingestApi.getQueueStatus();
        setStatus(data);
      } catch (error) {
        console.error('Failed to fetch queue status:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-32" />;

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Queue Status</h3>
      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-3">
          <Clock className="h-5 w-5 text-yellow-500" />
          <div>
            <p className="text-2xl font-bold">{status.pending}</p>
            <p className="text-sm text-muted-foreground">Pending</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
          <div>
            <p className="text-2xl font-bold">{status.processing}</p>
            <p className="text-sm text-muted-foreground">Processing</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <CheckCircle className="h-5 w-5 text-green-500" />
          <div>
            <p className="text-2xl font-bold">{status.completed}</p>
            <p className="text-sm text-muted-foreground">Completed</p>
          </div>
        </div>
      </div>
    </div>
  );
}
