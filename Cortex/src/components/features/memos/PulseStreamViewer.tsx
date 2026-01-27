import { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, Terminal, Globe, Zap, Clock } from 'lucide-react';

interface PulseEvent {
  event_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  session_id: string | null;
  timestamp: string;
}

interface PulseEventRowProps {
  event: PulseEvent;
}

function PulseEventRow({ event }: PulseEventRowProps) {
  const getIcon = () => {
    switch (event.event_type) {
      case 'file_save':
        return <FileText className="w-3 h-3" />;
      case 'terminal_cmd':
        return <Terminal className="w-3 h-3" />;
      case 'api_call':
        return <Globe className="w-3 h-3" />;
      case 'consolidation':
        return <Zap className="w-3 h-3 text-yellow-500" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const getEventColor = () => {
    switch (event.event_type) {
      case 'consolidation':
        return 'bg-yellow-500/10 border-yellow-500/20';
      case 'error':
        return 'bg-red-500/10 border-red-500/20';
      default:
        return 'bg-muted/50 border-border';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const formatPayload = (payload: Record<string, unknown>) => {
    if (event.event_type === 'consolidation') {
      return `→ OmegaKG (${payload.event_count} events)`;
    }
    if (event.event_type === 'file_save' && payload.file) {
      return payload.file as string;
    }
    if (event.event_type === 'terminal_cmd' && payload.command) {
      return payload.command as string;
    }
    if (event.event_type === 'api_call' && payload.endpoint) {
      return payload.endpoint as string;
    }
    return JSON.stringify(payload);
  };

  return (
    <div 
      className={`flex items-start gap-2 p-2 rounded border text-xs font-mono mb-1 ${getEventColor()}`}
    >
      <div className="flex items-center gap-1 min-w-[70px] text-muted-foreground">
        {getIcon()}
        <span>{formatTime(event.timestamp)}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-foreground">{event.event_type}</div>
        <div className="text-muted-foreground truncate">{formatPayload(event.payload)}</div>
      </div>
    </div>
  );
}

export function PulseStreamViewer() {
  const [events, setEvents] = useState<PulseEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Connect to SSE stream
    const connectSSE = () => {
      try {
        const eventSource = new EventSource('/api/memos/pulse/stream');
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setIsConnected(true);
          setError(null);
        };

        eventSource.onerror = (e) => {
          console.error('SSE connection error:', e);
          setIsConnected(false);
          setError('Connection lost');
          
          // Attempt reconnection after 5 seconds
          setTimeout(() => {
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
            }
            connectSSE();
          }, 5000);
        };

        eventSource.addEventListener('pulse', (e) => {
          try {
            const event = JSON.parse(e.data) as PulseEvent;
            setEvents(prev => {
              const updated = [...prev, event];
              // Keep last 50 events
              return updated.slice(-50);
            });
          } catch (err) {
            console.error('Failed to parse pulse event:', err);
          }
        });

        eventSource.addEventListener('ping', () => {
          // Keepalive, no action needed
        });

      } catch (err) {
        console.error('Failed to connect to SSE:', err);
        setError('Failed to connect');
      }
    };

    connectSSE();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          Live Pulse Stream
        </CardTitle>
        <Badge variant={isConnected ? "default" : "destructive"}>
          {error ? error : `${events.length} events`}
        </Badge>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto min-h-0">
        {events.length === 0 ? (
          <div className="text-center text-muted-foreground text-xs py-8">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Waiting for pulse events...</p>
            <p className="text-xs mt-1">Events will appear here in real-time</p>
          </div>
        ) : (
          <div className="space-y-1">
            {events.map((event) => (
              <PulseEventRow key={event.event_id} event={event} />
            ))}
            <div ref={scrollRef} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
