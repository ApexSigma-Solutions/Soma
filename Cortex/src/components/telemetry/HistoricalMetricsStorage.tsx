import { useEffect, useState } from 'react';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TrendingUp, Database, Cpu, Activity } from 'lucide-react';

interface MetricPoint {
  timestamp: string;
  value: number;
  label: string;
}

interface ServiceMetrics {
  service: string;
  data: MetricPoint[];
}

export function HistoricalMetricsStorage() {
  const [metrics, setMetrics] = useState<ServiceMetrics[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<'latency' | 'requests' | 'errors'>('latency');

  useEffect(() => {
    // Generate mock historical data
    const services = ['InGress', 'InGest', 'OmegaKG', 'memOS'];
    const now = new Date();
    
    const mockMetrics: ServiceMetrics[] = services.map((service) => {
      const data: MetricPoint[] = Array.from({ length: 24 }, (_, i) => {
        const time = new Date(now.getTime() - (23 - i) * 60 * 60 * 1000);
        let value: number;
        
        switch (selectedMetric) {
          case 'latency':
            value = Math.random() * 500 + 50; // 50-550ms
            break;
          case 'requests':
            value = Math.floor(Math.random() * 1000) + 100; // 100-1100 requests
            break;
          case 'errors':
            value = Math.floor(Math.random() * 50); // 0-50 errors
            break;
          default:
            value = 0;
        }
        
        return {
          timestamp: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          value: Math.round(value),
          label: service,
        };
      });

      return { service, data };
    });

    setMetrics(mockMetrics);
  }, [selectedMetric]);

  const getMetricIcon = () => {
    switch (selectedMetric) {
      case 'latency':
        return <Activity className="h-5 w-5" />;
      case 'requests':
        return <Database className="h-5 w-5" />;
      case 'errors':
        return <Cpu className="h-5 w-5" />;
      default:
        return <TrendingUp className="h-5 w-5" />;
    }
  };

  const getMetricColor = (index: number): string => {
    const colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b'];
    return colors[index % colors.length];
  };

  // Combine all data for the chart
  const chartData = metrics[0]?.data.map((point, i) => {
    const entry: Record<string, number | string> = {
      timestamp: point.timestamp,
    };
    metrics.forEach((metric) => {
      entry[metric.service] = metric.data[i]?.value || 0;
    });
    return entry;
  }) || [];

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          {getMetricIcon()}
          Historical Metrics
        </h3>
        <div className="flex gap-2">
          {(['latency', 'requests', 'errors'] as const).map((metric) => (
            <button
              key={metric}
              onClick={() => setSelectedMetric(metric)}
              className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors ${
                selectedMetric === metric
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              }`}
            >
              {metric}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <XAxis
              dataKey="timestamp"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickLine={false}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
            />
            {metrics.map((metric, index) => (
              <Area
                key={metric.service}
                type="monotone"
                dataKey={metric.service}
                stroke={getMetricColor(index)}
                fill={getMetricColor(index)}
                fillOpacity={0.1}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex flex-wrap gap-4">
        {metrics.map((metric, index) => {
          const avg = metric.data.reduce((sum, d) => sum + d.value, 0) / metric.data.length;
          return (
            <div key={metric.service} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getMetricColor(index) }}
              />
              <span className="text-sm text-muted-foreground">
                {metric.service}: {Math.round(avg)}
                {selectedMetric === 'latency' ? 'ms' : ''}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
