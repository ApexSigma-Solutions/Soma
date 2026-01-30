import { useEffect, useRef, useState } from 'react';

export interface NeuralPulseEvent {
  source_id: string;
  fact_units: Array<{
    text: string;
    entity_mentions: string[];
    temporal_anchor?: string;
  }>;
  metadata: {
    source: string;
    event_type: string;
    entropy: number;
    timestamp: string;
  };
}

export interface UseNeuralPulseReturn {
  events: NeuralPulseEvent[];
  connected: boolean;
  error: string | null;
  latestEvent: NeuralPulseEvent | null;
}

const BUFFER_SIZE = 50;

export function useNeuralPulse(url: string = 'http://localhost:8000/api/v1/telemetry/stream'): UseNeuralPulseReturn {
  const [events, setEvents] = useState<NeuralPulseEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latestEvent, setLatestEvent] = useState<NeuralPulseEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Initialize SSE connection
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('[useNeuralPulse] SSE connection opened');
      setConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        // Skip ping messages
        if (!event.data || event.data === ': ping') return;

        const data = JSON.parse(event.data);
        
        // Check for error messages
        if (data.error) {
          setError(data.error);
          return;
        }

        // Parse the payload if it's a string
        let pulseEvent: NeuralPulseEvent;
        if (typeof data.payload === 'string') {
          pulseEvent = JSON.parse(data.payload);
        } else {
          pulseEvent = data;
        }

        setLatestEvent(pulseEvent);
        
        // Add to buffer with size limit
        setEvents(prev => {
          const updated = [pulseEvent, ...prev];
          return updated.slice(0, BUFFER_SIZE);
        });

        console.log('[useNeuralPulse] Pulse received:', pulseEvent.source_id);
      } catch (err) {
        console.error('[useNeuralPulse] Parse error:', err);
        setError('Failed to parse event data');
      }
    };

    eventSource.onerror = (err) => {
      console.error('[useNeuralPulse] SSE error:', err);
      setConnected(false);
      setError('Connection lost to neural stream');
    };

    // Cleanup on unmount
    return () => {
      console.log('[useNeuralPulse] Closing SSE connection');
      eventSource.close();
    };
  }, [url]);

  return { events, connected, error, latestEvent };
}
