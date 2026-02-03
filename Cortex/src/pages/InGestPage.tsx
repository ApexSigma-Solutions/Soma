import { IngestionPlayground } from '@/components/ingest/IngestionPlayground';
import { QueueStatusDisplay } from '@/components/ingest/QueueStatusDisplay';
import { PipelineStageVisualization } from '@/components/ingest/PipelineStageVisualization';
import { CircuitBreakerIndicator } from '@/components/ingest/CircuitBreakerIndicator';
import { DigestStatsDashboard } from '@/components/ingest/DigestStatsDashboard';

export function InGestPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">InGest - Stomach</h1>
        <p className="text-muted-foreground">
          Text processing pipeline with SimpleMem stages
        </p>
      </div>

      {/* Queue Status and Circuit Breaker */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QueueStatusDisplay />
        <CircuitBreakerIndicator />
      </div>

      {/* Pipeline Visualization */}
      <PipelineStageVisualization />

      {/* Ingestion Playground */}
      <IngestionPlayground />

      {/* Digest Statistics */}
      <DigestStatsDashboard />
    </div>
  );
}
