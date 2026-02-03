import { useState } from 'react';
import { useSSEConnection } from '@/lib/api/sseConnection';
import { ingressApi } from '@/lib/api/ingressApi';
import { Activity, Wifi, WifiOff } from 'lucide-react';

interface PulseEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
  source: 'ingress' | 'ingest' | 'omegakg' | 'memos';
}

export function UnifiedPulseDisplay() {
  const [events, setEvents] = useState<PulseEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const MAX_EVENTS = 50;

  const streamUrl = ingressApi.getTelemetryStreamUrl();

  useSSEConnection({
    url: streamUrl,
    onMessage: (message) => {
      const newEvent: PulseEvent = {
        type: message.type,
        data: message.data as Record<string, unknown>,
        timestamp: message.timestamp || new Date().toISOString(),
        source: 'ingress',
      };

      setEvents((prev) => {
        const updated = [newEvent, ...prev];
        return updated.slice(0, MAX_EVENTS);
      });
    },
    onOpen: () => setIsConnected(true),
    onClose: () => setIsConnected(false),
    onError: () => setIsConnected(false),
  });

  const getSourceColor = (source: string): string => {
    const colors: Record<string, string> = {
      ingress: 'text-blue-500',
      ingest: 'text-green-500',
      omegakg: 'text-purple-500',
      memos: 'text-orange-500',
    };
    return colors[source] || 'text-gray-500';
  };

  const getEventIcon = (type: string) => {
    if (type.includes('error') || type.includes('fail')) return '🔴';
    if (type.includes('success') || type.includes('complete')) return '🟢';
    if (type.includes('warn')) return '🟡';
    return '🔵';
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Unified Pulse Stream
        </h3>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-500">Live</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-red-500" />
              <span className="text-sm text-red-500">Disconnected</span>
            </>
          )}
        </div>
      </div>

      <div className="h-64 overflow-y-auto bg-background rounded-md border border-border p-4 space-y-2 font-mono text-sm">
        {events.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            {isConnected ? 'Waiting for pulse events...' : 'Connecting to pulse stream...'}
          </p>
        ) : (
          events.map((event, index) => (
            <div
              key={`${event.timestamp}-${index}`}
              className="flex items-start gap-3 p-2 hover:bg-muted/30 rounded transition-colors"
            >
              <span className="text-lg">{getEventIcon(event.type)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-semibold text-xs uppercase ${getSourceColor(event.source)}`}>
                    {event.source}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-foreground truncate">
                  {event.type}: {JSON.stringify(event.data).slice(0, 100)}
                  {JSON.stringify(event.data).length > 100 ? '...' : ''}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-2 text-xs text-muted-foreground flex justify-between">
        <span>{events.length} events (max {MAX_EVENTS})</span>
        <span>Sources: InGress, InGest, OmegaKG, memOS</span>
      </div>
    </div>
  );
}
