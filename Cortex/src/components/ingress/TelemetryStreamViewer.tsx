import { useState, useEffect } from 'react';
import { useSSEConnection } from '@/lib/api/sseConnection';
import { ingressApi } from '@/lib/api/ingressApi';
import type { TelemetryEvent } from '@/lib/api/types/ingress';
import { Activity, Pause, Play, Trash2 } from 'lucide-react';

const MAX_EVENTS = 100;

export function TelemetryStreamViewer() {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const streamUrl = ingressApi.getTelemetryStreamUrl();

  const { disconnect } = useSSEConnection({
    url: streamUrl,
    onMessage: (message) => {
      if (!isPaused) {
        const newEvent: TelemetryEvent = {
          type: message.type,
          data: message.data as Record<string, unknown>,
          timestamp: message.timestamp || new Date().toISOString(),
        };
        
        setEvents((prev) => {
          const updated = [newEvent, ...prev];
          return updated.slice(0, MAX_EVENTS); // Keep only last 100 events
        });
      }
    },
    onOpen: () => {
      setIsConnected(true);
    },
    onClose: () => {
      setIsConnected(false);
    },
    onError: () => {
      setIsConnected(false);
    },
  });

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const handleClear = () => {
    setEvents([]);
  };

  const handleTogglePause = () => {
    setIsPaused(!isPaused);
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Telemetry Stream
          <span className={`ml-2 h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
        </h3>

        <div className="flex gap-2">
          <button
            onClick={handleTogglePause}
            className="px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-md transition-colors text-sm flex items-center gap-2"
          >
            {isPaused ? (
              <>
                <Play className="h-4 w-4" />
                Resume
              </>
            ) : (
              <>
                <Pause className="h-4 w-4" />
                Pause
              </>
            )}
          </button>

          <button
            onClick={handleClear}
            className="px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-md transition-colors text-sm flex items-center gap-2"
          >
            <Trash2 className="h-4 w-4" />
            Clear
          </button>
        </div>
      </div>

      <div className="h-96 overflow-y-auto bg-background rounded-md border border-border p-4 space-y-2 font-mono text-sm">
        {events.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            {isConnected ? 'Waiting for events...' : 'Connecting to stream...'}
          </p>
        ) : (
          events.map((event, index) => (
            <div
              key={`${event.timestamp}-${index}`}
              className="border-l-2 border-primary/50 pl-3 py-2 hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-start justify-between mb-1">
                <span className="text-primary font-semibold">{event.type}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(event.timestamp || '').toLocaleTimeString()}
                </span>
              </div>
              <pre className="text-xs text-foreground/80 whitespace-pre-wrap break-all">
                {JSON.stringify(event.data, null, 2)}
              </pre>
            </div>
          ))
        )}
      </div>

      <div className="mt-2 text-xs text-muted-foreground">
        {events.length} events (max {MAX_EVENTS})
        {isPaused && ' • Paused'}
      </div>
    </div>
  );
}
