import { useState } from 'react';
import { Webhook, ChevronDown, ChevronRight } from 'lucide-react';

interface WebhookEvent {
  id: string;
  source: 'github' | 'linear' | 'vault' | 'chrome' | 'terminal';
  event_type: string;
  timestamp: string;
  status: 'success' | 'failed';
  payload_preview: string;
}

// Mock data - will be replaced with real API when available
const mockEvents: WebhookEvent[] = [
  {
    id: '1',
    source: 'github',
    event_type: 'push',
    timestamp: new Date().toISOString(),
    status: 'success',
    payload_preview: 'Pushed 3 commits to main',
  },
  {
    id: '2',
    source: 'linear',
    event_type: 'issue.created',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    status: 'success',
    payload_preview: 'Issue SMA-123 created',
  },
];

export function WebhookActivityLog() {
  const [events] = useState<WebhookEvent[]>(mockEvents);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const getSourceColor = (source: string): string => {
    const colors = {
      github: 'text-purple-500',
      linear: 'text-blue-500',
      vault: 'text-orange-500',
      chrome: 'text-green-500',
      terminal: 'text-cyan-500',
    };
    return colors[source as keyof typeof colors] || 'text-gray-500';
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Webhook className="h-5 w-5 text-primary" />
        Webhook Activity Log
      </h3>

      <div className="space-y-2">
        {events.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No webhook events received yet
          </p>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className="bg-background border border-border rounded-md p-3 hover:bg-muted/30 transition-colors cursor-pointer"
              onClick={() => setExpandedId(expandedId === event.id ? null : event.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {expandedId === event.id ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className={`font-semibold uppercase text-sm ${getSourceColor(event.source)}`}>
                    {event.source}
                  </span>
                  <span className="text-sm text-foreground">{event.event_type}</span>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      event.status === 'success'
                        ? 'bg-green-500/20 text-green-500'
                        : 'bg-red-500/20 text-red-500'
                    }`}
                  >
                    {event.status}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>

              {expandedId === event.id && (
                <div className="mt-3 pt-3 border-t border-border">
                  <p className="text-sm text-muted-foreground mb-2">Preview:</p>
                  <p className="text-sm font-mono bg-muted/50 p-2 rounded">
                    {event.payload_preview}
                  </p>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-border text-xs text-muted-foreground">
        {events.length} events in last 24 hours
      </div>
    </div>
  );
}
