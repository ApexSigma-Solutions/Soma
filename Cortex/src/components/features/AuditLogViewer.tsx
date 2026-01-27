import * as React from "react"
import { useAuditLogStore, AuditAction } from '@/lib/store/useAuditLogStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  ScrollText, Trash2, Database, Inbox, Search, LogIn, 
  AlertTriangle, XCircle, FileText, Activity, ShieldAlert,
  ArrowRightCircle, CheckCircle2, RefreshCcw
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { captureApi, LogSummaryReport } from '@/lib/api/client';

const actionIcons: Record<AuditAction, typeof Inbox> = {
  capture: Inbox,
  ingest: Database,
  search: Search,
  login: LogIn,
  logout: LogIn,
  alert: AlertTriangle,
  error: XCircle,
};

const actionColors: Record<AuditAction, string> = {
  capture: 'text-blue-400',
  ingest: 'text-green-400',
  search: 'text-purple-400',
  login: 'text-cyan-400',
  logout: 'text-gray-400',
  alert: 'text-amber-400',
  error: 'text-red-400',
};

export function AuditLogViewer() {
  const { logs, clearLogs } = useAuditLogStore();
  const [summary, setSummary] = React.useState<LogSummaryReport | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);

  const fetchSummary = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await captureApi.getLogSummary();
      if (response.status === 'success' && response.report) {
        setSummary(response.report);
      }
    } catch (err) {
      console.error('Failed to fetch log summary:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <Card className="h-full flex flex-col glass-panel border-teal-500/10 overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b border-border/10 bg-black/5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-teal-500/10 border border-teal-500/20">
            <ScrollText className="h-4 w-4 text-teal-400" />
          </div>
          <div>
            <CardTitle className="text-sm font-black uppercase tracking-[0.2em] italic">Intelligence Log</CardTitle>
            <CardDescription className="text-[9px] font-mono uppercase tracking-widest text-teal-500/50">System Activity Monitoring</CardDescription>
          </div>
        </div>
        <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="h-7 text-[10px] font-mono hover:bg-teal-500/10" onClick={fetchSummary}>
               <RefreshCcw className={`h-3 w-3 mr-1 ${isLoading ? 'animate-spin' : ''}`} /> Sync
            </Button>
            {logs.length > 0 && (
                <Button variant="ghost" size="sm" className="h-7 text-[10px] font-mono hover:bg-destructive/10 text-destructive/70" onClick={clearLogs}>
                    <Trash2 className="h-3 w-3 mr-1" /> Purge
                </Button>
            )}
        </div>
      </CardHeader>
      
      <Tabs defaultValue="activity" className="flex-1 flex flex-col min-h-0">
        <div className="px-4 py-2 border-b border-border/5 bg-black/2">
          <TabsList className="grid w-full grid-cols-2 bg-transparent h-8 gap-2">
            <TabsTrigger value="activity" className="data-[state=active]:bg-teal-500/10 data-[state=active]:text-teal-400 text-[10px] font-mono uppercase tracking-widest border border-transparent data-[state=active]:border-teal-500/20">
              <Activity className="h-3 w-3 mr-2" /> Live Stream
            </TabsTrigger>
            <TabsTrigger value="summary" className="data-[state=active]:bg-teal-500/10 data-[state=active]:text-teal-400 text-[10px] font-mono uppercase tracking-widest border border-transparent data-[state=active]:border-teal-500/20">
              <FileText className="h-3 w-3 mr-2" /> Summary Report
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="activity" className="flex-1 min-h-0 m-0 relative">
          <CardContent className="h-full overflow-auto pt-4 pb-4">
            {logs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-30">
                <Activity className="h-10 w-10 mb-2 animate-pulse" />
                <p className="text-[10px] font-mono uppercase tracking-[0.2em]">Ready for stream...</p>
              </div>
            ) : (
              <div className="space-y-3">
                {logs.map((log) => {
                  const Icon = actionIcons[log.action];
                  return (
                    <div
                      key={log.id}
                      className="group flex items-start gap-4 p-3 rounded bg-black/5 border border-border/5 hover:border-teal-500/20 transition-all duration-300"
                    >
                      <div className={`p-2 rounded bg-black/20 ${actionColors[log.action]} group-hover:scale-110 transition-transform`}>
                        <Icon size={14} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                            <span className={`text-[9px] font-mono font-black uppercase tracking-widest ${actionColors[log.action]}`}>
                                {log.action}
                            </span>
                            <span className="text-[9px] text-muted-foreground font-mono">
                                {formatDistanceToNow(log.timestamp, { addSuffix: true })}
                            </span>
                        </div>
                        <p className="text-xs text-foreground/80 leading-relaxed font-medium">
                            {log.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </TabsContent>

        <TabsContent value="summary" className="flex-1 min-h-0 m-0">
          <CardContent className="h-full overflow-auto pt-4 pb-4">
            {!summary ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-30">
                <FileText className="h-10 w-10 mb-2" />
                <p className="text-[10px] font-mono uppercase tracking-[0.2em]">No report found</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Statistics Grid */}
                <div>
                   <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-teal-500 mb-3 flex items-center gap-2">
                       <Activity className="h-3 w-3" /> Network Statistics ({summary.date})
                   </h4>
                   <div className="grid grid-cols-2 gap-3">
                      {summary.stats.map((stat, idx) => (
                        <div key={idx} className="bg-black/20 border border-border/10 p-2 rounded flex justify-between items-center group hover:border-teal-500/30 transition-colors">
                           <div className="flex flex-col">
                              <span className="text-[8px] text-muted-foreground font-mono uppercase tracking-tighter">{stat.service}</span>
                              <span className={`text-[10px] font-mono font-bold uppercase ${stat.level === 'ERROR' ? 'text-red-400' : stat.level === 'WARNING' ? 'text-amber-400' : 'text-teal-400'}`}>
                                 {stat.level}
                              </span>
                           </div>
                           <span className="text-lg font-mono font-black text-foreground tabular-nums group-hover:text-teal-400 transition-colors">{stat.count}</span>
                        </div>
                      ))}
                   </div>
                </div>

                {/* Critical Errors */}
                {summary.critical_errors.length > 0 && (
                   <div>
                      <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-red-500 mb-3 flex items-center gap-2">
                          <ShieldAlert className="h-3 w-3" /> Critical Anomalies
                      </h4>
                      <div className="space-y-2">
                        {summary.critical_errors.map((error, idx) => (
                           <div key={idx} className="p-3 bg-red-500/5 border border-red-500/20 rounded relative overflow-hidden group">
                              <div className="absolute top-0 right-0 p-1 bg-red-500/10 text-red-500 text-[8px] font-mono font-bold uppercase transition-all duration-300">
                                 Count: {error.count}
                              </div>
                              <div className="flex items-center gap-2 mb-1">
                                 <Badge variant="error" className="h-4 p-0 px-2 text-[8px] uppercase tracking-tighter">{error.service}</Badge>
                                 <span className="text-[8px] text-muted-foreground font-mono">
                                    {new Date(error.timestamp).toLocaleTimeString()}
                                 </span>
                              </div>
                              <p className="text-[11px] text-red-200/90 font-mono leading-tight">
                                 {error.message}
                              </p>
                           </div>
                        ))}
                      </div>
                   </div>
                )}

                {/* Warnings */}
                {summary.warnings.length > 0 && (
                   <div>
                      <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-amber-500 mb-3 flex items-center gap-2">
                          <AlertTriangle className="h-3 w-3" /> Warnings Observed
                      </h4>
                      <div className="space-y-1">
                        {summary.warnings.map((warning, idx) => (
                           <div key={idx} className="flex gap-2 items-start text-[10px] font-mono text-muted-foreground bg-black/5 p-1.5 rounded border border-transparent hover:border-amber-500/10 transition-colors">
                              <div className="w-1.5 h-1.5 rounded-full bg-amber-500/40 mt-1 shrink-0"></div>
                              <span className="leading-relaxed">{warning}</span>
                           </div>
                        ))}
                      </div>
                   </div>
                )}

                {/* Suggested Actions */}
                {summary.suggested_actions.length > 0 && (
                   <div className="pt-2">
                      <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-cyan-400 mb-3 flex items-center gap-2">
                          <ArrowRightCircle className="h-3 w-3" /> Recommended Mitigations
                      </h4>
                      <div className="space-y-2">
                        {summary.suggested_actions.map((action, idx) => (
                           <div key={idx} className="flex items-start gap-3 p-2.5 bg-cyan-500/5 border border-cyan-500/10 rounded group">
                              <div className="mt-0.5">
                                 <CheckCircle2 size={12} className="text-cyan-400 opacity-50 group-hover:opacity-100 transition-opacity" />
                              </div>
                              <p className="text-[10px] font-mono text-cyan-200/80 leading-normal">
                                 {action}
                              </p>
                           </div>
                        ))}
                      </div>
                   </div>
                )}
                
                <div className="pt-4 text-center">
                    <p className="text-[8px] font-mono uppercase tracking-[0.3em] text-muted-foreground/50">
                        Report Sequence End // Gen: {new Date(summary.generated_at).toLocaleTimeString()}
                    </p>
                </div>
              </div>
            )}
          </CardContent>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
