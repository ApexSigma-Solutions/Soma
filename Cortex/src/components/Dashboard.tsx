import { useState, useEffect } from 'react';
import { useSystemStore } from '@/lib/store/systemStore';
import { useToastStore } from '@/lib/store/useToastStore';
import type { ApiHealth } from '@/lib/api/client';
import {
  Activity,
  Database,
  Server,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { healthPoller } from '@/lib/api/healthPoller';

export function Dashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [apiHealth, setApiHealth] = useState<ApiHealth[]>([]);
  const { addToast } = useToastStore();
  const { setApiHealth: setStoreApiHealth } = useSystemStore();

  const fetchHealth = async () => {
    try {
      const health = await healthPoller.checkAllHealth();
      setApiHealth(health);
      setStoreApiHealth(health);
    } catch (error) {
      console.error('Failed to fetch health:', error);
      addToast('Failed to fetch service health', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (healthy: boolean) => {
    return healthy ? (
      <CheckCircle2 className="h-5 w-5 text-green-500" />
    ) : (
      <AlertCircle className="h-5 w-5 text-red-500" />
    );
  };

  const getStatusBadge = (healthy: boolean) => {
    return healthy ? (
      <Badge variant="default" className="bg-green-500/20 text-green-500 hover:bg-green-500/30">
        Online
      </Badge>
    ) : (
      <Badge variant="destructive" className="bg-red-500/20 text-red-500 hover:bg-red-500/30">
        Offline
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-4 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            System overview and health status
          </p>
        </div>
        <Button onClick={fetchHealth} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Service Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {apiHealth.map((api) => (
          <Card key={api.name} className={api.healthy ? 'border-green-500/30' : 'border-red-500/30'}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                {api.name}
              </CardTitle>
              {getStatusIcon(api.healthy)}
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                {getStatusBadge(api.healthy)}
                <span className="text-xs text-muted-foreground">
                  {api.latency !== undefined ? `${api.latency.toFixed(1)}ms` : '--'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Last checked: {api.lastChecked ? new Date(api.lastChecked).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--'}
              </p>
              {api.error && (
                <p className="text-xs text-red-500 mt-1 truncate" title={api.error}>
                  {api.error}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {apiHealth.filter(api => api.healthy).length}/{apiHealth.length}
            </div>
            <p className="text-xs text-muted-foreground">
              Services online
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {apiHealth.length > 0 && apiHealth.some(api => api.latency !== undefined)
                ? `${Math.round(apiHealth.reduce((sum, api) => sum + (api.latency || 0), 0) / apiHealth.filter(api => api.latency !== undefined).length)}ms`
                : '--'}
            </div>
            <p className="text-xs text-muted-foreground">
              Average across all services
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Update</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {apiHealth.length > 0 && apiHealth[0]?.lastChecked
                ? new Date(apiHealth[0].lastChecked).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })
                : '--'}
            </div>
            <p className="text-xs text-muted-foreground">
              Last health check
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
