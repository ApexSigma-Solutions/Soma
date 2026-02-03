import { useEffect, useState } from 'react';
import { ingestApi } from '@/lib/api/client';
import type { PipelineStats } from '@/lib/api/types/ingest';
import { ArrowRight, CheckCircle, Loader2 } from 'lucide-react';

export function PipelineStageVisualization() {
  const [stats, setStats] = useState<PipelineStats | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await ingestApi.getPipelineStats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch pipeline stats:', error);
      }
    };

    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-32" />;

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">SimpleMem Pipeline</h3>
      <div className="flex items-center justify-between gap-2">
        {stats.stages.map((stage, index) => (
          <div key={stage.name} className="flex items-center gap-2 flex-1">
            <div className="flex-1 p-3 bg-background rounded-md border border-border text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                {stage.status === 'processing' ? (
                  <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                <p className="font-semibold text-sm">{stage.name}</p>
              </div>
              {stage.last_processed && (
                <p className="text-xs text-muted-foreground">
                  {new Date(stage.last_processed).toLocaleTimeString()}
                </p>
              )}
            </div>
            {index < stats.stages.length - 1 && (
              <ArrowRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
