import { SemanticSearchInterface } from '@/components/omegakg/SemanticSearchInterface';
import { AtomicFactBrowser } from '@/components/omegakg/AtomicFactBrowser';
import { KnowledgeCommitTracker } from '@/components/omegakg/KnowledgeCommitTracker';
import { CodexViolationDisplay } from '@/components/omegakg/CodexViolationDisplay';
import { Neo4jGraphVisualization } from '@/components/omegakg/Neo4jGraphVisualization';

export function OmegaKGPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">OmegaKG - Brain</h1>
        <p className="text-muted-foreground">
          Knowledge graph persistence and semantic search
        </p>
      </div>

      {/* Semantic Search */}
      <SemanticSearchInterface />

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AtomicFactBrowser />
        <KnowledgeCommitTracker />
      </div>

      {/* Codex Violations */}
      <CodexViolationDisplay />

      {/* Graph Visualization */}
      <Neo4jGraphVisualization />
    </div>
  );
}
