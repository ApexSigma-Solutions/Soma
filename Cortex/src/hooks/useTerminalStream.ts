import { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '@/lib/store/useAuthStore';

export interface LogEntry {
  id: string;
  type: 'system' | 'thought' | 'error' | 'input' | 'message';
  text: string;
  timestamp: number;
  level: 'INFO' | 'WARN' | 'ERROR';
  source: string;
  content: string;
}

export interface TelemetryState {
  scratchpad: string[];
  working_memory: Record<string, string>;
  lastUpdate: number;
  logs: LogEntry[];
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
}

const MAX_LOGS = 100;

export const useTerminalStream = (sessionId: string = 'default_session') => {
  const [data, setData] = useState<TelemetryState>({
    scratchpad: [],
    working_memory: {},
    lastUpdate: 0,
    logs: [],
    isConnected: false,
    connectionState: 'disconnected',
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const { token } = useAuthStore();
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8765';

  // Helper to manually add logs (defined inside useTerminalStream to access setData)
  const addLog = (entry: Omit<LogEntry, 'id' | 'timestamp'>) => {
    setData(prev => {
      const newLog: LogEntry = {
        ...entry,
        id: crypto.randomUUID(),
        timestamp: Date.now(),
      };
      const newLogs = [...prev.logs, newLog].slice(-MAX_LOGS);
      return { ...prev, logs: newLogs };
    });
  };

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
        // Fix potential double-slash issue
        const normalizedBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
        const url = new URL(`${normalizedBaseUrl}/api/v1/telemetry/stream`);
        url.searchParams.append('session_id', sessionId);
        
        console.log('[Terminal] Attempting connection:', url.toString());
        setData(prev => ({ ...prev, connectionState: 'connecting' }));
        
        addLog({ 
            type: 'system', 
            text: `Establishing neural link to [${sessionId}]...`, 
            level: 'INFO', 
            source: 'SYS', 
            content: `Establishing neural link to [${sessionId}]...` 
        });

        const es = new EventSource(url.toString());
        eventSourceRef.current = es;

        es.onopen = () => {
          console.log('[Terminal] Connected');
          setData(prev => ({ ...prev, isConnected: true, connectionState: 'connected' }));
          addLog({ 
              type: 'system', 
              text: `Connected to Telemetry Stream [${sessionId}]`, 
              level: 'INFO', 
              source: 'SYS', 
              content: `Connected to Telemetry Stream [${sessionId}]` 
          });
        };

        es.onmessage = (event) => {
          try {
            if (event.data === 'ping') return;
            
            const payload = JSON.parse(event.data);
            const { scratchpad, working_memory, timestamp, content, level, source } = payload;
            
            let logLevel: 'INFO' | 'WARN' | 'ERROR' = 'INFO';
            if (level) logLevel = level;
            else if (content && (content.includes('[ERROR]') || content.includes('Error:'))) logLevel = 'ERROR';
            else if (content && (content.includes('[WARN]') || content.includes('Warning:'))) logLevel = 'WARN';

            const logContent = content || JSON.stringify(payload);
            
            const newLogEntry: Omit<LogEntry, 'id' | 'timestamp'> = {
                type: logLevel === 'ERROR' ? 'error' : 'system',
                text: logContent,
                content: logContent,
                level: logLevel,
                source: source || 'UKN'
            };
            
            setData(prev => {
                const newLog = {
                    ...newLogEntry,
                    id: crypto.randomUUID(),
                    timestamp: Date.now()
                };
                
                return {
                  ...prev,
                  scratchpad: scratchpad || prev.scratchpad,
                  working_memory: working_memory || prev.working_memory,
                  lastUpdate: timestamp || Date.now(),
                  logs: [...prev.logs, newLog].slice(-MAX_LOGS)
                };
            });

          } catch (err) {
            console.error('Telemetry parse error:', err);
          }
        };

        // Handle custom 'error' events from backend
        es.addEventListener('error', (event: any) => {
            try {
                const payload = JSON.parse(event.data);
                addLog({
                    type: 'error',
                    text: `STREAM_ERROR: ${payload.message || 'Unknown stream error'}`,
                    content: payload.message || 'Unknown stream error',
                    level: 'ERROR',
                    source: 'SSE'
                });
            } catch (e) {
                // Not a JSON error, likely a connection error handled by es.onerror
            }
        });

        es.onerror = (err) => {
          console.error('SSE Connection Error:', err);
          setData(prev => ({ ...prev, isConnected: false, connectionState: 'error' }));
          
          addLog({ 
              type: 'error', 
              text: 'Neural link severed. Retrying in 5s...', 
              level: 'ERROR', 
              source: 'SSE',
              content: 'Connection lost'
          });
          
          es.close();
          retryTimeout = setTimeout(connect, 5000);
        };
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      clearTimeout(retryTimeout);
    };
  }, [sessionId, token, baseUrl]);

  const clearLogs = () => setData(prev => ({ ...prev, logs: [] }));

  return {
      ...data,
      clearLogs
  };
};
