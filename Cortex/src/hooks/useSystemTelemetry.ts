/**
 * Unified System Telemetry Hook
 * ApexSigma Naming: camelCase for hooks with 'use' prefix
 * 
 * Aggregates real-time telemetry from all three biological systems:
 * - Senses (InGress): Neural pulse events with entropy filtering
 * - Stomach (InGest): System health and queue metrics
 * - Brain (OmegaKG): Knowledge graph metrics
 */
import { useState, useEffect, useCallback } from 'react';
import type {
  SystemTelemetry,
  NeuralPulseEvent,
  SystemHealth,
  BrainMetrics,
} from '@/types/telemetry';

interface UseSystemTelemetryOptions {
  sensesUrl?: string;
  stomachUrl?: string;
  brainUrl?: string;
  maxEvents?: number;
}

interface UseSystemTelemetryReturn {
  telemetry: SystemTelemetry;
  connected: boolean;
  error: string | null;
  reconnect: () => void;
}

const DEFAULT_OPTIONS: UseSystemTelemetryOptions = {
  sensesUrl: 'http://localhost:8000/api/v1/telemetry/stream',
  stomachUrl: 'http://localhost:8766/vitals/stream',
  brainUrl: 'http://localhost:8765/api/v1/telemetry/stream',
  maxEvents: 50,
};

export function useSystemTelemetry(
  options: UseSystemTelemetryOptions = {}
): UseSystemTelemetryReturn {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  const [telemetry, setTelemetry] = useState<SystemTelemetry>({
    senses: {
      eventBuffer: [],
      reductionRate: 0,
      lastEntropy: 0,
      connected: false,
    },
    stomach: {
      queueDepth: 0,
      processingRate: 0,
      vitals: {
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        queue_depth: 0,
        processing_rate: 0,
        timestamp: new Date().toISOString(),
      },
      connected: false,
    },
    brain: {
      nodeCount: 0,
      avgConnectivity: 0,
      embeddingDimension: 768,
      connected: false,
    },
  });
  
  const [error, setError] = useState<string | null>(null);
  
  const reconnect = useCallback(() => {
    setError(null);
    setTelemetry({
      senses: { eventBuffer: [], reductionRate: 0, lastEntropy: 0, connected: false },
      stomach: {
        queueDepth: 0,
        processingRate: 0,
        vitals: {
          cpu_percent: 0,
          memory_percent: 0,
          disk_percent: 0,
          queue_depth: 0,
          processing_rate: 0,
          timestamp: new Date().toISOString(),
        },
        connected: false,
      },
      brain: { nodeCount: 0, avgConnectivity: 0, embeddingDimension: 768, connected: false },
    });
  }, []);
  
  useEffect(() => {
    // Connect to InGress (Senses) telemetry
    const sensesSource = new EventSource(opts.sensesUrl!);
    
    // Connect to InGest (Stomach) telemetry
    const stomachSource = new EventSource(opts.stomachUrl!);
    
    // Connect to OmegaKG (Brain) telemetry
    const brainSource = new EventSource(opts.brainUrl!);
    
    // Senses event handler
    sensesSource.onmessage = (event) => {
      try {
        const data: NeuralPulseEvent = JSON.parse(event.data);
        
        setTelemetry((prev) => ({
          ...prev,
          senses: {
            eventBuffer: [data, ...prev.senses.eventBuffer].slice(0, opts.maxEvents),
            reductionRate: data.metadata.reduction_rate || calculateReductionRate(data),
            lastEntropy: data.metadata.entropy,
            connected: true,
          },
        }));
      } catch (err) {
        console.error('Senses telemetry parse error:', err);
      }
    };
    
    sensesSource.onerror = () => {
      setTelemetry((prev) => ({
        ...prev,
        senses: { ...prev.senses, connected: false },
      }));
      setError('Senses telemetry connection lost');
    };
    
    // Stomach event handler
    stomachSource.onmessage = (event) => {
      try {
        const data: SystemHealth = JSON.parse(event.data);
        
        setTelemetry((prev) => ({
          ...prev,
          stomach: {
            queueDepth: data.queue_depth || 0,
            processingRate: data.processing_rate || 0,
            vitals: data,
            connected: true,
          },
        }));
      } catch (err) {
        console.error('Stomach telemetry parse error:', err);
      }
    };
    
    stomachSource.onerror = () => {
      setTelemetry((prev) => ({
        ...prev,
        stomach: { ...prev.stomach, connected: false },
      }));
      setError('Stomach telemetry connection lost');
    };
    
    // Brain event handler
    brainSource.onmessage = (event) => {
      try {
        const data: BrainMetrics = JSON.parse(event.data);
        
        setTelemetry((prev) => ({
          ...prev,
          brain: {
            nodeCount: data.node_count || 0,
            avgConnectivity: data.avg_connectivity || 0,
            embeddingDimension: data.embedding_dimension || 768,
            connected: true,
          },
        }));
      } catch (err) {
        console.error('Brain telemetry parse error:', err);
      }
    };
    
    brainSource.onerror = () => {
      setTelemetry((prev) => ({
        ...prev,
        brain: { ...prev.brain, connected: false },
      }));
      setError('Brain telemetry connection lost');
    };
    
    // Cleanup
    return () => {
      sensesSource.close();
      stomachSource.close();
      brainSource.close();
    };
  }, [opts.sensesUrl, opts.stomachUrl, opts.brainUrl, opts.maxEvents]);
  
  const allConnected =
    telemetry.senses.connected &&
    telemetry.stomach.connected &&
    telemetry.brain.connected;
  
  return {
    telemetry,
    connected: allConnected,
    error,
    reconnect,
  };
}

function calculateReductionRate(event: NeuralPulseEvent): number {
  // Calculate entropy filtering reduction
  // (events filtered / total events) * 100
  if (!event.metadata.entropy) return 0;
  
  // If entropy is below threshold, this event was filtered
  const threshold = 0.35;
  return event.metadata.entropy < threshold ? 100 : 0;
}
