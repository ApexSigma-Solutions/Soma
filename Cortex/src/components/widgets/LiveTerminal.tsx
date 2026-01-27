import { useEffect, useRef } from 'react';
import { Terminal, Wifi, WifiOff } from 'lucide-react';
import { useTerminalStream } from '@/hooks/useTerminalStream';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function LiveTerminal() {
  const { logs, isConnected } = useTerminalStream();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Card className="h-full flex flex-col bg-card glass-panel border-teal-500/10 shadow-tech-lg overflow-hidden min-h-[400px]">
      <CardHeader className="py-3 px-4 border-b border-border/10 bg-black/5 flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-sm bg-teal-500/10 border border-teal-500/20">
            <Terminal className="h-4 w-4 text-teal-400" />
          </div>
          <CardTitle className="text-sm font-mono tracking-wider text-foreground uppercase">
            Ecosystem Live Stream
          </CardTitle>
        </div>
        <div className="flex items-center gap-3">
          <Badge 
            variant="outline" 
            className={`
              font-mono text-[10px] uppercase h-5 px-2 border-0
              ${isConnected 
                ? 'bg-emerald-500/10 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]' 
                : 'bg-red-500/10 text-red-400 shadow-[0_0_8px_rgba(239,68,68,0.4)]'}
            `}
          >
            {isConnected ? 'ONLINE' : 'DISCONNECTED'}
          </Badge>
          {isConnected ? (
             <Wifi className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
          ) : (
             <WifiOff className="h-3.5 w-3.5 text-red-400" />
          )}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 p-0 relative group">
        {/* CRT Scanline Effect Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] z-10 pointer-events-none bg-[length:100%_4px,3px_100%]"></div>
        
        <div className="h-full w-full overflow-y-auto p-4 font-mono text-xs scrollbar-thin scrollbar-thumb-cyan-900/50 scrollbar-track-transparent" ref={scrollRef}>
          <div className="space-y-1 pb-4">
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-slate-600 gap-2 font-mono">
                <span className="text-2xl animate-pulse">_</span>
                <span>Waiting for telemetry...</span>
              </div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="flex gap-3 hover:bg-white/5 py-0.5 px-1 rounded transition-colors group/line">
                  <span className="text-slate-500 shrink-0 w-16 text-[10px] pt-[2px]">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span className={`
                    break-all text-slate-300 group-hover/line:text-cyan-50 transition-colors
                    ${log.level === 'ERROR' ? 'text-red-400 font-bold' : ''}
                    ${log.level === 'WARN' ? 'text-amber-400' : ''}
                    ${log.level === 'INFO' ? 'text-cyan-200' : ''}
                    ${log.content.includes('[SYSTEM]') ? 'text-purple-400 font-bold' : ''}
                  `}>
                    <span className="opacity-50 mr-2 border-r border-slate-700 pr-2 inline-block w-6 text-center">{log.source.substring(0,2).toUpperCase()}</span>
                    {log.content}
                  </span>
                </div>
              ))
            )}
            
            {/* Blinking Cursor at bottom */}
            {isConnected && (
              <div className="h-4 w-2 bg-cyan-500/80 animate-pulse mt-2 ml-10 shadow-[0_0_5px_cyan]"></div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
