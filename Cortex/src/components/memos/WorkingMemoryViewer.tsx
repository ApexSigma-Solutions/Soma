import { useState, useEffect } from 'react';
import { memosApi } from '@/lib/api/client';
import type { WorkingMemory } from '@/lib/api/types/memos';
import { Brain, RefreshCw } from 'lucide-react';

interface WorkingMemoryViewerProps {
  sessionId?: string;
}

export function WorkingMemoryViewer({ sessionId = 'default' }: WorkingMemoryViewerProps) {
  const [memory, setMemory] = useState<WorkingMemory | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const data = await memosApi.getWorkingMemory(sessionId);
      setMemory(data);
    } catch (error) {
      console.error('Failed to fetch working memory:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
    const interval = setInterval(fetchMemory, 10000);
    return () => clearInterval(interval);
  }, [sessionId]);

  if (loading && !memory) {
    return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-48" />;
  }

  if (!memory) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          Working Memory
        </h3>
        <button
          onClick={fetchMemory}
          disabled={loading}
          className="p-2 hover:bg-muted rounded-md transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {Object.entries(memory).map(([key, value]) => (
          <div
            key={key}
            className="flex items-start justify-between p-3 bg-background rounded-md border border-border"
          >
            <span className="text-sm font-medium text-muted-foreground capitalize">
              {key.replace(/_/g, ' ')}
            </span>
            <span className="text-sm text-foreground font-mono">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
