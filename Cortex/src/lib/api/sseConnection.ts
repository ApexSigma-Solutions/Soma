import { useEffect, useRef, useCallback } from 'react';

export interface SSEMessage {
  type: string;
  data: unknown;
  timestamp: string;
}

export interface SSEConnectionConfig {
  url: string;
  onMessage: (message: SSEMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

export class SSEConnectionManager {
  private eventSource: EventSource | null = null;
  private config: SSEConnectionConfig;
  private reconnectAttempts = 0;
  private reconnectTimeout?: number;
  private isClosed = false;

  constructor(config: SSEConnectionConfig) {
    this.config = {
      reconnectDelay: 3000,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  connect(): void {
    if (this.eventSource) {
      return; // Already connected
    }

    this.isClosed = false;
    this.eventSource = new EventSource(this.config.url);

    this.eventSource.onopen = () => {
      console.log(`SSE connected: ${this.config.url}`);
      this.reconnectAttempts = 0;
      this.config.onOpen?.();
    };

    this.eventSource.onmessage = (event) => {
      try {
        const message: SSEMessage = JSON.parse(event.data);
        this.config.onMessage(message);
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      this.config.onError?.(error);
      this.handleConnectionError();
    };
  }

  private handleConnectionError(): void {
    this.close();

    if (this.isClosed) {
      return; // Manually closed, don't reconnect
    }

    const maxAttempts = this.config.maxReconnectAttempts || 5;
    if (this.reconnectAttempts < maxAttempts) {
      const delay = this.config.reconnectDelay || 3000;
      console.log(`Reconnecting SSE in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${maxAttempts})`);
      
      this.reconnectTimeout = window.setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, delay);
    } else {
      console.error('Max SSE reconnection attempts reached');
    }
  }

  close(): void {
    this.isClosed = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = undefined;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.config.onClose?.();
    }
  }

  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }
}

// React hook for SSE connections
export function useSSEConnection(config: SSEConnectionConfig) {
  const managerRef = useRef<SSEConnectionManager | null>(null);

  const connect = useCallback(() => {
    if (!managerRef.current) {
      managerRef.current = new SSEConnectionManager(config);
    }
    managerRef.current.connect();
  }, [config]);

  const disconnect = useCallback(() => {
    managerRef.current?.close();
    managerRef.current = null;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connect,
    disconnect,
    isConnected: managerRef.current?.isConnected() || false,
  };
}
