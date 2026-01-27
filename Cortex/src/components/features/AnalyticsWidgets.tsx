import { useAnalyticsStore } from '@/lib/store/useAnalyticsStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Inbox, Database, Search, Clock } from 'lucide-react';

export function AnalyticsWidgets() {
  const { totalCaptures, totalIngestions, totalSearches, activeSessionMinutes } = useAnalyticsStore();

  const metrics = [
    { label: 'Captures', value: totalCaptures, icon: Inbox, color: 'text-cyan-400', glow: 'shadow-[0_0_8px_rgba(6,182,212,0.3)]' },
    { label: 'Ingestions', value: totalIngestions, icon: Database, color: 'text-emerald-400', glow: 'shadow-[0_0_8px_rgba(16,185,129,0.3)]' },
    { label: 'Searches', value: totalSearches, icon: Search, color: 'text-purple-400', glow: 'shadow-[0_0_8px_rgba(168,85,247,0.3)]' },
    { 
      label: 'Session', 
      value: `${activeSessionMinutes}M`, 
      icon: Clock, 
      color: 'text-amber-400',
      glow: 'shadow-[0_0_8px_rgba(245,158,11,0.3)]'
    },
  ];

  return (
    <Card className="bg-card glass-panel border-teal-500/10 overflow-hidden relative group">
      {/* HUD Decorative Element */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rotate-45 -mr-12 -mt-12 group-hover:bg-cyan-500/10 transition-colors"></div>
      
      <CardHeader className="pb-4 border-b border-border/10 px-6">
        <CardTitle className="text-sm font-mono uppercase tracking-[0.2em] flex items-center gap-2 text-muted-foreground">
          <TrendingUp className="h-4 w-4 text-teal-400" /> 
          Neural Throughput Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {metrics.map(({ label, value, icon: Icon, color, glow }) => (
            <div key={label} className="relative flex flex-col items-center">
              <div className={`
                w-12 h-12 rounded-lg bg-black/10 border border-border/10
                flex items-center justify-center mb-3 group/metric cursor-default
                ${glow} transition-all duration-300
              `}>
                <Icon className={`h-6 w-6 ${color}`} />
              </div>
              <div className="flex flex-col items-center">
                <div className="text-3xl font-bold text-foreground font-mono tracking-tighter tabular-nums">
                    {value}
                </div>
                <div className="text-[10px] text-cyan-400 font-mono tracking-widest uppercase mt-1">
                    {label}
                </div>
              </div>
              
              {/* Corner Accents */}
              <div className="absolute top-0 right-0 w-1 h-1 bg-cyan-500/20"></div>
              <div className="absolute bottom-0 left-0 w-1 h-1 bg-cyan-500/20"></div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
