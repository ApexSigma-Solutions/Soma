import { useTerminalStream } from '@/hooks/useTerminalStream';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Activity, Clock, Zap, BarChart3, ShieldAlert } from 'lucide-react';

export function TelemetryWidget() {
  const { logs, connectionState } = useTerminalStream();
  
  // Calculate stats from the recent logs buffer
  const errorCount = logs.filter(l => l.level === 'ERROR').length;
  const warnCount = logs.filter(l => l.level === 'WARN').length;
  
  // Calculate throughput (estimates)
  const throughput = logs.length > 5 ? (logs.length / 30).toFixed(1) : "0.0";

  const getStatusColor = () => {
    if (connectionState === 'connected') return 'text-emerald-400 bg-emerald-500/10 shadow-[0_0_8px_rgba(16,185,129,0.3)]';
    if (connectionState === 'connecting') return 'text-amber-400 bg-amber-500/10 animate-pulse';
    return 'text-red-400 bg-red-500/10 shadow-[0_0_8px_rgba(239,68,68,0.3)]';
  };

  return (
    <Card className="h-full bg-card glass-panel border-teal-500/10 shadow-tech-lg group overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-teal-500/50 to-transparent"></div>
      
      <CardHeader className="pb-2 relative pt-6 px-6">
         <CardTitle className="flex items-center gap-2 text-sm font-mono tracking-[0.2em] text-muted-foreground uppercase">
            <BarChart3 className="h-4 w-4 text-teal-400" />
            Neural Telemetry
         </CardTitle>
         <CardDescription className="text-[10px] text-teal-400 font-mono tracking-widest mt-1">REAL-TIME_FEED_01</CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4 pt-4 px-6">
        {/* Connection Status Panel */}
        <div className={`p-3 rounded border border-border/20 transition-all duration-500 ${getStatusColor()}`}>
            <div className="flex justify-between items-center">
                <div className="flex flex-col">
                    <span className="text-[9px] uppercase font-mono tracking-tighter opacity-70">Link State</span>
                    <span className="text-sm font-bold font-mono tracking-widest">
                        {connectionState.toUpperCase()}
                    </span>
                </div>
                <Activity size={18} className={connectionState === 'connecting' ? 'animate-spin' : ''} />
            </div>
        </div>

        {/* Grid Stats */}
        <div className="grid grid-cols-2 gap-3">
            {/* Errors */}
            <div className="bg-black/10 p-3 rounded border border-border/10 flex flex-col gap-1 group/stat hover:border-red-500/30 transition-colors">
                <div className="flex justify-between items-center opacity-60">
                    <span className="text-[8px] uppercase font-mono tracking-widest">Errors</span>
                    <ShieldAlert size={10} className={errorCount > 0 ? 'text-red-400' : ''} />
                </div>
                <div className={`text-xl font-mono font-bold ${errorCount > 0 ? 'text-red-400' : 'text-foreground/90'}`}>
                    {String(errorCount).padStart(2, '0')}
                </div>
            </div>

            {/* Warnings */}
            <div className="bg-black/10 p-3 rounded border border-border/10 flex flex-col gap-1 group/stat hover:border-amber-500/30 transition-colors">
                <div className="flex justify-between items-center opacity-60">
                    <span className="text-[8px] uppercase font-mono tracking-widest">Warnings</span>
                    <Zap size={10} className={warnCount > 0 ? 'text-amber-400' : ''} />
                </div>
                <div className={`text-xl font-mono font-bold ${warnCount > 0 ? 'text-amber-400' : 'text-foreground/90'}`}>
                    {String(warnCount).padStart(2, '0')}
                </div>
            </div>

            {/* Throughput */}
            <div className="bg-black/10 p-3 rounded border border-border/10 flex flex-col gap-1 col-span-2 hover:border-teal-500/30 transition-colors">
                <div className="flex justify-between items-center opacity-60">
                    <span className="text-[8px] uppercase font-mono tracking-widest">Rate (evt/sec)</span>
                    <Clock size={10} />
                </div>
                <div className="flex items-end gap-2">
                    <div className="text-2xl font-mono font-bold text-foreground">
                        {throughput}
                    </div>
                    {/* Tiny visual chart hint */}
                    <div className="flex gap-0.5 items-end h-6 pb-1">
                        {[4, 7, 3, 8, 5, 6].map((h, i) => (
                            <div key={i} className="w-1 bg-cyan-500/30 hover:bg-cyan-500 transition-colors" style={{ height: `${h * 10}%` }}></div>
                        ))}
                    </div>
                </div>
            </div>
        </div>

        {/* Footer Meta */}
        <div className="pt-2 border-t border-border/10">
            <div className="flex justify-between text-[8px] font-mono text-muted-foreground tracking-tighter">
                <span>BUFFER_CAP: 100_ENTRIES</span>
                <span>ENC: AES_256</span>
            </div>
        </div>
      </CardContent>

      {/* Grid Pattern Corner */}
      <div className="absolute bottom-0 right-0 w-8 h-8 opacity-10 pointer-events-none">
          <svg viewBox="0 0 40 40" className="w-full h-full text-cyan-500 fill-current">
              <path d="M0 0h1v1H0zM5 0h1v1H5zM10 0h1v1H10zM15 0h1v1H15zM20 0h1v1H20zM25 0h1v1H25zM30 0h1v1H30zM35 0h1v1H35zM0 5h1v1H0zM0 10h1v1H10zM0 15h1v1H15zM0 20h1v1H20zM0 25h1v1H25zM0 30h1v1H30zM0 35h1v1H35z" />
          </svg>
      </div>
    </Card>
  );
}
