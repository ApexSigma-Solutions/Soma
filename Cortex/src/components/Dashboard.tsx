import { useEffect } from 'react';
import { Activity, CheckCircle2, XCircle, Clock, Play, Square, Cpu, Server, Database, Globe, RotateCcw } from 'lucide-react';
import { useSystemStore } from '@/lib/store/systemStore';
import { healthPoller } from '@/lib/api/healthPoller';
import { ApiHealth, captureApi, ingestApi } from '@/lib/api/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AuditLogViewer } from '@/components/features/AuditLogViewer';
import { useAnalyticsStore } from '@/lib/store/useAnalyticsStore';

import { AnalyticsWidgets } from '@/components/features/AnalyticsWidgets';
import { LiveTerminal } from '@/components/widgets/LiveTerminal';
import { TelemetryWidget } from '@/components/widgets/TelemetryWidget';

export function Dashboard() {
  const { apiHealth, setApiHealth } = useSystemStore();

  useEffect(() => {
    // Start health polling
    healthPoller.start();

    // Subscribe to health updates
    const unsubscribe = healthPoller.subscribe((health: ApiHealth[]) => {
      setApiHealth(health);
    });

    // Fetch initial stats and set up polling for metrics
    const fetchStats = async () => {
      try {
        const [omegaStats, ingestStats] = await Promise.all([
          captureApi.getStats().catch(() => null),
          ingestApi.getStats().catch(() => null)
        ]);

        const metrics: Record<string, number> = {};
        if (omegaStats) {
          metrics.totalCaptures = omegaStats.total_captures;
        }
        if (ingestStats) {
          metrics.totalIngestions = ingestStats.throughput_24h; 
        }
        
        if (Object.keys(metrics).length > 0) {
          useAnalyticsStore.getState().setMetrics(metrics);
        }
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
      }
    };

    fetchStats();
    const statsInterval = window.setInterval(fetchStats, 30000); // Pulse every 30s

    return () => {
      unsubscribe();
      healthPoller.stop();
      clearInterval(statsInterval);
    };
  }, [setApiHealth]);

  const handleControl = (name: string, action: 'start' | 'stop' | 'restart') => {
      // Cast to any to bypass generic build issues
      captureApi.controlService(name, action).then(() => healthPoller.checkNow());
  };

  const getServiceIcon = (name: string) => {
    switch(name.toLowerCase()) {
      case 'omega': return <Cpu className="w-4 h-4" />;
      case 'ingest': return <Database className="w-4 h-4" />;
      case 'memos': return <Server className="w-4 h-4" />;
      default: return <Globe className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-8 pb-10">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black text-foreground tracking-tighter uppercase italic">
            Command <span className="text-teal-500">Dashboard</span>
          </h2>
          <p className="text-teal-500 font-mono text-[10px] uppercase tracking-[0.3em] font-bold mt-1">
            Core Systems Oversight & Management
          </p>
        </div>
        <div className="flex items-center gap-2 bg-teal-500/10 border border-teal-500/20 rounded-lg px-4 py-2 glass-panel">
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse shadow-[0_0_8px_rgba(0,191,166,0.8)]"></div>
            <span className="text-[10px] text-foreground font-mono uppercase tracking-widest font-bold">Neural Link Active</span>
        </div>
      </div>

      {/* Analytics */}
      <AnalyticsWidgets />

      {/* Deep Observability Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-teal-500/20 pb-2">
            <Activity className="w-4 h-4 text-teal-400" />
            <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground font-bold">Deep Observability</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
           <div className="lg:col-span-3 h-[500px]">
              <LiveTerminal />
           </div>
           <div className="h-[500px]">
               <TelemetryWidget />
           </div>
        </div>
      </div>

      {/* API Status Panel */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 border-b border-teal-500/20 pb-2">
            <Server className="w-4 h-4 text-teal-400" />
            <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground font-bold">System Infrastructure</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {apiHealth.length === 0 ? (
            <Card className="col-span-3 bg-card glass-panel border-teal-500/10">
              <CardContent>
                <div className="text-center py-12">
                  <Activity className="mx-auto mb-3 text-teal-900 animate-pulse" size={64} />
                  <p className="text-teal-700 font-mono text-xs tracking-widest text-center font-bold">INITIALIZING SCAN...</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            apiHealth.map((api: ApiHealth) => (
              <Card key={api.name} className="bg-card glass-panel border-teal-500/10 hover:border-teal-500/40 transition-all duration-500 group overflow-hidden">
                {/* HUD Top Bar */}
                <div className={`h-1 w-full transition-all duration-300 ${api.healthy ? 'bg-teal-500 shadow-[0_0_15px_rgba(0,191,166,0.6)]' : 'bg-destructive shadow-[0_0_15px_rgba(215,38,56,0.6)]'}`}></div>
                
                <CardHeader className="py-4 bg-black/5 flex flex-row items-center justify-between space-y-0 border-b border-border/10">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-teal-500/10 border border-teal-500/20 group-hover:border-teal-500/50 transition-colors">
                        {getServiceIcon(api.name)}
                    </div>
                    <div>
                        <CardTitle className="text-base font-black tracking-tighter text-foreground uppercase italic">{api.name}</CardTitle>
                        <div className="text-[9px] text-teal-400 font-mono tracking-widest font-bold">SYS_NODE::{api.name.toUpperCase()}</div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                      {api.healthy ? (
                        <div className="flex items-center gap-1.5 text-teal-500 animate-pulse">
                          <CheckCircle2 size={12} />
                          <span className="text-[10px] font-mono font-black tracking-widest">ONLINE</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-destructive animate-pulse">
                          <XCircle size={12} />
                          <span className="text-[10px] font-mono font-black tracking-widest">OFFLINE</span>
                        </div>
                      )}
                  </div>
                </CardHeader>
                
                <CardContent className="pt-6 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                      <div className="bg-black/10 border border-border/10 p-2 rounded">
                          <div className="text-[9px] text-muted-foreground font-mono uppercase font-bold tracking-widest block mb-1">Latency</div>
                          <div className="flex items-center gap-2">
                             <Clock size={12} className="text-teal-500/70" />
                             <span className="text-sm font-mono text-foreground font-bold tabular-nums">
                                {api.responseTime !== undefined ? `${api.responseTime.toFixed(1)}ms` : '--'}
                             </span>
                          </div>
                      </div>
                      <div className="bg-black/10 border border-border/10 p-2 rounded">
                         <div className="text-[9px] text-muted-foreground font-mono uppercase font-bold tracking-widest block mb-1">Sync</div>
                         <span className="text-[10px] font-mono text-muted-foreground font-bold">
                            {api.lastChecked.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                         </span>
                      </div>
                  </div>

                  {api.error && (
                    <div className="p-2 bg-destructive/10 border border-destructive/20 rounded">
                      <span className="text-destructive text-[10px] font-mono leading-none break-all font-bold">
                        EXCEPTION: {api.error}
                      </span>
                    </div>
                  )}
                  
                  <div className="flex gap-2 pt-2">
                    {api.healthy ? (
                      <>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="flex-[2] h-9 rounded-sm bg-destructive/10 border border-destructive/20 text-destructive hover:bg-destructive hover:text-white transition-all text-[10px] font-black uppercase tracking-[0.2em]" 
                          onClick={() => handleControl(api.name, 'stop')} 
                          disabled={false}
                        >
                          <Square className="w-3 h-3 mr-2" fill="currentColor" /> Terminate
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="flex-1 h-9 rounded-sm bg-amber-500/10 border border-amber-500/20 text-amber-500 hover:bg-amber-500 hover:text-white transition-all text-[10px] font-black uppercase tracking-[0.2em]" 
                          onClick={() => handleControl(api.name, 'restart')} 
                          disabled={false}
                          title="Restart Service"
                        >
                          <RotateCcw className="w-3 h-3" />
                        </Button>
                      </>
                    ) : (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="flex-1 h-9 rounded-sm bg-teal-500/10 border border-teal-500/20 text-teal-500 hover:bg-teal-500 hover:text-white transition-all text-[10px] font-black uppercase tracking-[0.2em]" 
                        onClick={() => handleControl(api.name, 'start')} 
                        disabled={false}
                      >
                        <Play className="w-3 h-3 mr-2" fill="currentColor" /> Initialize
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Bottom Section: Audit Log & System Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <AuditLogViewer />

        <Card className="bg-card glass-panel border-teal-500/10">
          <CardHeader>
            <CardTitle className="text-sm font-black uppercase tracking-[0.2em] text-muted-foreground italic">System Topology</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6 pt-2">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground font-mono font-bold uppercase tracking-wider">NODE_OMEGA</span>
                <span className="text-foreground font-mono font-bold">PORT:8765</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground font-mono font-bold uppercase tracking-wider">NODE_INGEST</span>
                <span className="text-foreground font-mono font-bold">PORT:8766</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground font-mono font-bold uppercase tracking-wider">NODE_MEMOS</span>
                <span className="text-foreground font-mono font-bold">PORT:8768</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] text-muted-foreground font-mono font-bold uppercase tracking-wider">ACTIVE_INTERFACES</span>
                <span className="text-teal-500 font-mono font-black">03 / STABLE</span>
              </div>
            </div>
            {/* Minimal SVG Graphic */}
            <div className="mt-8 h-20 w-full flex items-center justify-center opacity-30">
                <div className="flex items-center gap-8 font-mono text-[8px] text-teal-500">
                    <div className="flex flex-col items-center">
                        <div className="w-10 h-10 border-2 border-teal-500 rotate-45 flex items-center justify-center mb-2 shadow-[0_0_10px_rgba(0,191,166,0.3)]">
                            <div className="w-6 h-6 border border-teal-500"></div>
                        </div>
                        CORE_MIND
                    </div>
                    <div className="h-[2px] w-20 bg-teal-500/30 relative">
                        <div className="absolute top-0 left-0 w-2 h-2 bg-teal-500 rounded-full -translate-y-1/2 shadow-[0_0_8px_rgba(0,191,166,0.8)]"></div>
                    </div>
                    <div className="flex flex-col items-center">
                        <div className="w-10 h-10 border-2 border-teal-500 flex items-center justify-center mb-2 shadow-[0_0_10px_rgba(0,191,166,0.3)]">
                            <div className="w-6 h-6 border-teal-500 border-t-2 border-l-2"></div>
                        </div>
                        NODES
                    </div>
                </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
