import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { captureApi, VectorHealth, ServiceHealth, OmegaStats } from '@/lib/api/client';
import { Activity, HardDrive, Zap, Globe } from 'lucide-react';

export function CaptureStatus() {
  const [vectorHealth, setVectorHealth] = useState<VectorHealth | null>(null);
  const [serviceHealth, setServiceHealth] = useState<ServiceHealth | null>(null);
  const [stats, setStats] = useState<OmegaStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [vHealth, sHealth, oStats] = await Promise.all([
        captureApi.getVectorHealth(),
        captureApi.getServiceHealth(),
        captureApi.getStats(),
      ]);
      setVectorHealth(vHealth);
      setServiceHealth(sHealth);
      setStats(oStats);
    } catch (error) {
      console.error('Failed to fetch capture metrics', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !vectorHealth) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Status</CardTitle>
        </CardHeader>
        <CardContent>Loading health metrics...</CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Overall Service Status */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Service Hub</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold capitalize">
              {stats?.postgres_status === 'ONLINE' ? 'Optimal' : 'Issues'}
            </div>
            <Badge variant={stats?.neo4j_status === 'ONLINE' ? 'success' : 'error'}>
              Neo4j {stats?.neo4j_status}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Vault: {serviceHealth?.vault_accessible ? 'Linked' : 'Missing'} | 
            Sessions: {stats?.active_sessions || 0}
          </p>
        </CardContent>
      </Card>

      {/* Capture Volume */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Capture Volume</CardTitle>
          <Globe className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {stats?.total_captures || 0}
          </div>
          <p className="text-xs text-muted-foreground">
            +{stats?.recent_captures_24h || 0} in last 24h
          </p>
        </CardContent>
      </Card>

      {/* Vector Queue */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Neural Queue</CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {vectorHealth?.pending_count || 0}
          </div>
          <p className="text-xs text-muted-foreground">
            Awaiting embedding
          </p>
        </CardContent>
      </Card>

       {/* Vector Store */}
       <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Vector Atlas</CardTitle>
          <HardDrive className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {vectorHealth?.total_records || 0}
          </div>
          <div className="flex items-center gap-2 mt-1">
             <Badge variant={vectorHealth?.worker_running ? 'success' : 'error'} className="text-[10px] py-0">
               {vectorHealth?.worker_running ? 'Agent Active' : 'Agent Idle'}
             </Badge>
             <span className="text-xs text-muted-foreground">
               Failures: {vectorHealth?.failed_count || 0}
             </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
