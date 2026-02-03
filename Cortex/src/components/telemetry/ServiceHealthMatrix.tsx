import { useEffect, useState } from 'react';
import { useSystemStore } from '@/lib/store/systemStore';
import type { ApiHealth } from '@/lib/api/client';
import { Server, CheckCircle, AlertCircle, XCircle, Activity } from 'lucide-react';

interface ServiceStatus {
  name: string;
  status: 'online' | 'degraded' | 'offline';
  latency?: number;
  lastCheck: string;
  error?: string;
}

export function ServiceHealthMatrix() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const apiHealth = useSystemStore((state) => state.apiHealth);

  useEffect(() => {
    const mappedServices: ServiceStatus[] = apiHealth.map((health: ApiHealth) => {
      let status: 'online' | 'degraded' | 'offline' = 'offline';
      if (health.healthy) {
        status = health.latency && health.latency < 1000 ? 'online' : 'degraded';
      }

      return {
        name: health.name,
        status,
        latency: health.latency,
        lastCheck: new Date().toISOString(),
        error: health.error,
      };
    });

    setServices(mappedServices);
  }, [apiHealth]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="h-6 w-6 text-yellow-500" />;
      case 'offline':
        return <XCircle className="h-6 w-6 text-red-500" />;
      default:
        return <Activity className="h-6 w-6 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'online':
        return 'bg-green-500/20 border-green-500/50';
      case 'degraded':
        return 'bg-yellow-500/20 border-yellow-500/50';
      case 'offline':
        return 'bg-red-500/20 border-red-500/50';
      default:
        return 'bg-muted border-border';
    }
  };

  const getPort = (name: string): string => {
    const ports: Record<string, string> = {
      'InGress': '8000',
      'InGest': '8766',
      'Omega': '8765',
      'Memos': '8768',
    };
    return ports[name] || '-';
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <Server className="h-5 w-5 text-primary" />
        Service Health Matrix
      </h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {services.map((service) => (
          <div
            key={service.name}
            className={`p-4 rounded-lg border-2 ${getStatusColor(service.status)} transition-all`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-sm">{service.name}</span>
              {getStatusIcon(service.status)}
            </div>

            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Port:</span>
                <span className="font-mono">{getPort(service.name)}</span>
              </div>

              {service.latency && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Latency:</span>
                  <span className={`font-mono ${service.latency > 1000 ? 'text-yellow-500' : 'text-green-500'}`}>
                    {service.latency}ms
                  </span>
                </div>
              )}

              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <span className={`capitalize font-medium ${
                  service.status === 'online' ? 'text-green-500' :
                  service.status === 'degraded' ? 'text-yellow-500' :
                  'text-red-500'
                }`}>
                  {service.status}
                </span>
              </div>

              {service.error && (
                <p className="text-red-500 text-xs mt-2 truncate" title={service.error}>
                  {service.error}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-border">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span>Online</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span>Degraded</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span>Offline</span>
          </div>
        </div>
      </div>
    </div>
  );
}
