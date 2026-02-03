import { UnifiedPulseDisplay } from '@/components/telemetry/UnifiedPulseDisplay';
import { ServiceHealthMatrix } from '@/components/telemetry/ServiceHealthMatrix';
import { HistoricalMetricsStorage } from '@/components/telemetry/HistoricalMetricsStorage';
import { MealTraceVisualization } from '@/components/telemetry/MealTraceVisualization';

export function TelemetryPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Telemetry</h1>
        <p className="text-muted-foreground">
          Real-time monitoring, health status, and system metrics
        </p>
      </div>

      {/* Service Health Matrix */}
      <ServiceHealthMatrix />

      {/* Unified Pulse and Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UnifiedPulseDisplay />
        <HistoricalMetricsStorage />
      </div>

      {/* Meal Trace */}
      <MealTraceVisualization />
    </div>
  );
}
