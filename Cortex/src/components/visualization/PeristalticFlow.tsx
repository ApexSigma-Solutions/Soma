/**
 * Peristaltic Flow Visualization Component
 * ApexSigma Naming: PascalCase for React components
 * 
 * Visualizes data movement through biological stages:
 * - Senses (InGress): Raw signal capture
 * - Stomach (InGest): Processing and digestion
 * - Brain (OmegaKG): Knowledge graph consolidation
 */
import { Activity, AlertCircle, CheckCircle2, Zap, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SystemTelemetry } from '@/types/telemetry';

interface PeristalticFlowProps {
  telemetry: SystemTelemetry;
}

export function PeristalticFlow({ telemetry }: PeristalticFlowProps) {
  const stages = [
    {
      name: 'Senses',
      biologicalName: 'Sensory Input Layer',
      icon: Activity,
      status: telemetry.senses.eventBuffer.length > 0 ? 'active' : 'idle',
      throughput: telemetry.senses.reductionRate,
      bottleneck: telemetry.senses.lastEntropy < 0.35,
      metrics: {
        'Event Buffer': telemetry.senses.eventBuffer.length,
        'Last Entropy': telemetry.senses.lastEntropy.toFixed(3),
        'Reduction Rate': `${telemetry.senses.reductionRate.toFixed(1)}%`,
      },
    },
    {
      name: 'Stomach',
      biologicalName: 'Digestive Processing',
      icon: telemetry.stomach.queueDepth > 100 ? AlertCircle : CheckCircle2,
      status: telemetry.stomach.processingRate > 0 ? 'active' : 'idle',
      throughput: telemetry.stomach.processingRate,
      bottleneck: telemetry.stomach.queueDepth > 100,
      metrics: {
        'Queue Depth': telemetry.stomach.queueDepth,
        'Processing Rate': `${telemetry.stomach.processingRate.toFixed(1)}/s`,
        'CPU Usage': `${telemetry.stomach.vitals.cpu_percent?.toFixed(1)}%`,
      },
    },
    {
      name: 'Brain',
      biologicalName: 'Knowledge Graph',
      icon: Brain,
      status: 'active',
      throughput: 0,
      bottleneck: false,
      metrics: {
        'Total Nodes': telemetry.brain.nodeCount,
        'Avg Connectivity': telemetry.brain.avgConnectivity.toFixed(2),
        'Embedding Dim': `${telemetry.brain.embeddingDimension}-dim`,
      },
    },
  ];

  return (
    <div className="flex items-center justify-between gap-8 p-6">
      {stages.map((stage, idx) => (
        <React.Fragment key={stage.name}>
          <StageNode {...stage} isBottleneck={stage.bottleneck} />
          {idx < stages.length - 1 && (
            <FlowArrow
              active={stage.status === 'active'}
              pulsing={stage.throughput > 50}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

interface StageNodeProps {
  name: string;
  biologicalName: string;
  icon: React.ComponentType<{ className?: string }>;
  status: 'active' | 'idle';
  throughput: number;
  isBottleneck: boolean;
  metrics: Record<string, string | number>;
}

function StageNode({
  name,
  biologicalName,
  icon: Icon,
  status,
  throughput,
  isBottleneck,
  metrics,
}: StageNodeProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 p-6 rounded-lg border-2 transition-all min-w-[200px]",
        status === 'active' && "border-green-500 bg-green-500/10",
        isBottleneck && "border-red-500 bg-red-500/10 animate-pulse"
      )}
    >
      <Icon
        className={cn(
          "w-12 h-12",
          status === 'active' ? "text-green-500" : "text-muted-foreground",
          isBottleneck && "text-red-500"
        )}
      />

      <div className="text-center">
        <p className="font-semibold text-lg">{name}</p>
        <p className="text-xs text-muted-foreground">{biologicalName}</p>

        <div className="mt-2 text-sm">
          <p className="font-mono">
            {throughput.toFixed(1)} <span className="text-muted-foreground">events/s</span>
          </p>
        </div>

        {isBottleneck && (
          <div className="mt-2 px-2 py-1 bg-red-500/20 rounded text-xs text-red-500 font-medium">
            ⚠ Bottleneck Detected
          </div>
        )}
      </div>

      {/* Metrics panel */}
      <div className="mt-3 w-full space-y-1 text-xs">
        {Object.entries(metrics).map(([key, value]) => (
          <div key={key} className="flex justify-between">
            <span className="text-muted-foreground">{key}:</span>
            <span className="font-mono">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface FlowArrowProps {
  active: boolean;
  pulsing: boolean;
}

function FlowArrow({ active, pulsing }: FlowArrowProps) {
  return (
    <div className="relative flex-1 h-2 bg-border rounded">
      <div
        className={cn(
          "absolute inset-0 h-full rounded bg-gradient-to-r from-green-500 to-blue-500 transition-all",
          active ? "opacity-100" : "opacity-20",
          pulsing && "animate-pulse"
        )}
      />

      {/* Animated dots for active flow */}
      {active && (
        <div className="absolute inset-0 flex items-center justify-around">
          <div className="w-1 h-1 bg-white rounded-full animate-ping" />
          <div className="w-1 h-1 bg-white rounded-full animate-ping delay-100" />
          <div className="w-1 h-1 bg-white rounded-full animate-ping delay-200" />
        </div>
      )}
    </div>
  );
}
