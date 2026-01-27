import { useEffect, useState, useRef } from 'react';
import { Cpu, HardDrive, Zap } from 'lucide-react';

interface VitalsData {
  cpu_percent: number;
  ram_percent: number;
  vram_percent?: number;
  timestamp: string;
}

export function SystemHUD() {
  const [vitals, setVitals] = useState<VitalsData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connectToVitals = () => {
      try {
        const eventSource = new EventSource('/api/ingest/vitals/stream');
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data: VitalsData = JSON.parse(event.data);
            setVitals(data);
          } catch (e) {
            console.error('Failed to parse vitals data:', e);
          }
        };

        eventSource.onerror = () => {
          setIsConnected(false);
          eventSource.close();
          // Reconnect after 5 seconds
          setTimeout(connectToVitals, 5000);
        };
      } catch (e) {
        console.error('Failed to connect to vitals stream:', e);
      }
    };

    connectToVitals();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const getCpuColor = (percent: number) => {
    if (percent < 50) return 'text-emerald-400 bg-emerald-500/20';
    if (percent < 80) return 'text-blue-400 bg-blue-500/20';
    return 'text-amber-400 bg-amber-500/20';
  };

  const getRamColor = (percent: number) => {
    if (percent < 70) return 'bg-emerald-500';
    if (percent < 90) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getVramColor = (percent: number) => {
    if (percent < 70) return 'bg-purple-500';
    return 'bg-purple-400';
  };

  const cpuPercent = vitals?.cpu_percent ?? 0;
  const ramPercent = vitals?.ram_percent ?? 0;
  const vramPercent = vitals?.vram_percent ?? 0;

  return (
    <div className="flex items-center gap-3">
      {/* Connection Status Indicator */}
      <div 
        className={`w-2 h-2 rounded-full ${
          isConnected 
            ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse' 
            : 'bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.8)]'
        }`}
        title={isConnected ? 'Vitals Stream Connected' : 'Vitals Stream Disconnected'}
      />

      {/* CPU Bar */}
      <div className="flex items-center gap-2">
        <Cpu size={14} className="text-blue-400" />
        <div className="w-20 h-2 bg-black/30 rounded-full overflow-hidden border border-border/20">
          <div 
            className={`h-full transition-all duration-300 ${getCpuColor(cpuPercent)}`}
            style={{ width: `${Math.min(cpuPercent, 100)}%` }}
          />
        </div>
        <span className="text-xs font-mono text-muted-foreground w-10">
          {Math.round(cpuPercent)}%
        </span>
      </div>

      {/* RAM Bar */}
      <div className="flex items-center gap-2">
        <HardDrive size={14} className="text-emerald-400" />
        <div className="w-20 h-2 bg-black/30 rounded-full overflow-hidden border border-border/20">
          <div 
            className={`h-full transition-all duration-300 ${getRamColor(ramPercent)}`}
            style={{ width: `${Math.min(ramPercent, 100)}%` }}
          />
        </div>
        <span className="text-xs font-mono text-muted-foreground w-10">
          {Math.round(ramPercent)}%
        </span>
      </div>

      {/* VRAM Bar (Optional) */}
      <div className="flex items-center gap-2">
        <Zap size={14} className="text-purple-400" />
        <div className="w-16 h-2 bg-black/30 rounded-full overflow-hidden border border-border/20">
          <div 
            className={`h-full transition-all duration-300 ${getVramColor(vramPercent)}`}
            style={{ width: `${Math.min(vramPercent, 100)}%` }}
          />
        </div>
        <span className="text-xs font-mono text-muted-foreground w-8">
          {Math.round(vramPercent)}%
        </span>
      </div>
    </div>
  );
}
