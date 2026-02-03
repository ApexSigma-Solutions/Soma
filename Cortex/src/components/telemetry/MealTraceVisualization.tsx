import { useState } from 'react';
import { ArrowRight, CheckCircle, Circle, Loader2 } from 'lucide-react';

interface MealStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  service: string;
  timestamp?: string;
}

export function MealTraceVisualization() {
  const [stages] = useState<MealStage[]>([
    {
      id: '1',
      name: 'Signal Capture',
      description: 'Raw signal ingested via InGress',
      status: 'completed',
      service: 'InGress',
      timestamp: new Date(Date.now() - 300000).toISOString(),
    },
    {
      id: '2',
      name: 'Raw Lake Storage',
      description: 'Signal stored in PostgreSQL raw_lake',
      status: 'completed',
      service: 'InGress',
      timestamp: new Date(Date.now() - 295000).toISOString(),
    },
    {
      id: '3',
      name: 'SimpleMem Processing',
      description: 'Entropy → Coreference → Temporal → Facts',
      status: 'processing',
      service: 'InGest',
      timestamp: new Date(Date.now() - 290000).toISOString(),
    },
    {
      id: '4',
      name: 'Redis Stream',
      description: 'Processed signal queued in Redis',
      status: 'pending',
      service: 'InGest',
    },
    {
      id: '5',
      name: 'Knowledge Graph Write',
      description: 'Atomic facts persisted to Neo4j',
      status: 'pending',
      service: 'OmegaKG',
    },
    {
      id: '6',
      name: 'Guardian Validation',
      description: 'Codex compliance verification',
      status: 'pending',
      service: 'OmegaKG',
    },
    {
      id: '7',
      name: 'Context Available',
      description: 'Signal available for agent retrieval',
      status: 'pending',
      service: 'memOS',
    },
  ]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'processing':
        return <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />;
      case 'failed':
        return <Circle className="h-6 w-6 text-red-500" />;
      default:
        return <Circle className="h-6 w-6 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 border-green-500/50';
      case 'processing':
        return 'bg-blue-500/20 border-blue-500/50';
      case 'failed':
        return 'bg-red-500/20 border-red-500/50';
      default:
        return 'bg-muted border-border';
    }
  };

  const getServiceColor = (service: string): string => {
    const colors: Record<string, string> = {
      'InGress': 'text-blue-500',
      'InGest': 'text-green-500',
      'OmegaKG': 'text-purple-500',
      'memOS': 'text-orange-500',
    };
    return colors[service] || 'text-muted-foreground';
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-xl font-semibold mb-4">Meal Trace Visualization</h3>
      <p className="text-sm text-muted-foreground mb-6">
        End-to-end signal flow through the Soma ecosystem
      </p>

      <div className="space-y-4">
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-start gap-4">
            {/* Connector line */}
            {index < stages.length - 1 && (
              <div className="absolute left-8 top-12 bottom-0 w-0.5 bg-border" />
            )}

            {/* Stage card */}
            <div className={`flex-1 p-4 rounded-lg border-2 ${getStatusColor(stage.status)} relative`}>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  {getStatusIcon(stage.status)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold">{stage.name}</h4>
                    <span className={`text-xs font-medium px-2 py-1 rounded ${getServiceColor(stage.service)} bg-muted`}>
                      {stage.service}
                    </span>
                  </div>

                  <p className="text-sm text-muted-foreground mb-2">
                    {stage.description}
                  </p>

                  {stage.timestamp && (
                    <p className="text-xs text-muted-foreground">
                      {new Date(stage.timestamp).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Arrow to next stage */}
            {index < stages.length - 1 && (
              <div className="flex items-center justify-center w-8 flex-shrink-0">
                <ArrowRight className="h-5 w-5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-border">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {stages.filter((s) => s.status === 'completed').length} of {stages.length} stages complete
          </span>
          <button
            onClick={() => window.open('#', '_blank')}
            className="text-primary hover:text-primary/80"
          >
            View Full Trace Log →
          </button>
        </div>
      </div>
    </div>
  );
}
