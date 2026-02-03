import { useEffect, useState, useRef } from 'react';
import { omegaKgApi } from '@/lib/api/client';
import type { GraphVisualization } from '@/lib/api/types/omegakg';
import { Share2, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';

export function Neo4jGraphVisualization() {
  const [graph, setGraph] = useState<GraphVisualization | null>(null);
  const [loading, setLoading] = useState(true);
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const data = await omegaKgApi.getGraphVisualization();
      setGraph(data);
    } catch (error) {
      console.error('Failed to fetch graph:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, []);

  const handleZoomIn = () => setScale(s => Math.min(2, s + 0.2));
  const handleZoomOut = () => setScale(s => Math.max(0.5, s - 0.2));
  const handleReset = () => setScale(1);

  if (loading) {
    return <div className="animate-pulse bg-card border border-border rounded-lg p-6 h-96" />;
  }

  if (!graph) return null;

  // Simple force-directed layout simulation
  const nodePositions = graph.nodes.map((node, i) => {
    const angle = (i / graph.nodes.length) * 2 * Math.PI;
    const radius = 150;
    return {
      ...node,
      x: 300 + radius * Math.cos(angle),
      y: 200 + radius * Math.sin(angle),
    };
  });

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold flex items-center gap-2">
          <Share2 className="h-5 w-5 text-primary" />
          Knowledge Graph
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="text-sm text-muted-foreground min-w-[3rem] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={handleReset}
            className="p-2 hover:bg-muted rounded-md transition-colors"
            title="Reset zoom"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="relative h-96 bg-background rounded-md border border-border overflow-hidden"
      >
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 600 400"
          style={{ transform: `scale(${scale})`, transformOrigin: 'center' }}
        >
          {/* Edges */}
          {graph.edges.map((edge) => {
            const sourceNode = nodePositions.find(n => n.id === edge.source);
            const targetNode = nodePositions.find(n => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;

            return (
              <line
                key={edge.id}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke="hsl(var(--muted-foreground))"
                strokeWidth="2"
                strokeOpacity="0.5"
              />
            );
          })}

          {/* Nodes */}
          {nodePositions.map((node) => (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r={node.label === 'AtomicFact' ? 20 : 15}
                fill={node.label === 'AtomicFact' ? 'hsl(var(--primary))' : 'hsl(var(--secondary))'}
                stroke="hsl(var(--border))"
                strokeWidth="2"
              />
              <text
                x={node.x}
                y={node.y + 35}
                textAnchor="middle"
                fill="hsl(var(--foreground))"
                fontSize="10"
              >
                {String(node.properties.name || node.id)}
              </text>
            </g>
          ))}
        </svg>

        <div className="absolute bottom-4 left-4 bg-card/90 backdrop-blur p-3 rounded-md border border-border text-xs">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-primary" />
            <span>AtomicFact ({graph.nodes.filter(n => n.label === 'AtomicFact').length})</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-secondary" />
            <span>Entity ({graph.nodes.filter(n => n.label === 'Entity').length})</span>
          </div>
          <div className="mt-2 text-muted-foreground">
            {graph.edges.length} relationships
          </div>
        </div>
      </div>
    </div>
  );
}
