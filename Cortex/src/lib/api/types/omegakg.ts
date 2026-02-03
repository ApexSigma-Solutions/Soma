// OmegaKG API TypeScript types

export interface AtomicFact {
  id: string;
  content: string;
  embedding?: number[];
  created_at: string;
  source?: string;
  confidence?: number;
  similarity?: number; // For search results
}

export interface SemanticSearchRequest {
  query: string;
  limit?: number;
  threshold?: number;
  hybrid?: boolean;
}

export interface SemanticSearchResult {
  facts: AtomicFact[];
  total: number;
  query_time_ms: number;
}

export interface KnowledgeCommit {
  id: string;
  status: 'pending' | 'validated' | 'rejected';
  facts_count: number;
  created_at: string;
  validated_at?: string;
  validator?: string;
}

export interface CodexViolation {
  id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  rule: string;
  message: string;
  context?: string;
  detected_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties?: Record<string, unknown>;
}

export interface GraphVisualization {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface OmegaStats {
  total_captures: number;
  recent_captures_24h: number;
  neo4j_status: 'connected' | 'disconnected';
  postgres_status: 'connected' | 'disconnected';
  active_sessions: number;
}
