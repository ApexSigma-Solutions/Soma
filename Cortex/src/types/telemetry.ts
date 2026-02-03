/**
 * Telemetry Type Definitions for Cortex Bridge
 * ApexSigma Naming: PascalCase for types/interfaces
 * 
 * Provides strict TypeScript types for telemetry data from:
 * - Senses (InGress)
 * - Stomach (InGest)
 * - Brain (OmegaKG)
 */

/**
 * Neural pulse event from InGress (Senses)
 * Represents a captured signal with entropy filtering
 */
export interface NeuralPulseEvent {
  source_id: string;
  fact_units: FactUnit[];
  metadata: {
    source: string;
    event_type: string;
    entropy: number;
    timestamp: string;
    reduction_rate?: number;
  };
}

/**
 * Atomic fact unit extracted from signals
 */
export interface FactUnit {
  id: string;
  content: string;
  entropy: number;
  tags: string[];
}

/**
 * System health metrics from InGest (Stomach)
 */
export interface SystemHealth {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  queue_depth: number;
  processing_rate: number;
  timestamp: string;
}

/**
 * Brain metrics from OmegaKG (Knowledge Graph)
 */
export interface BrainMetrics {
  node_count: number;
  avg_connectivity: number;
  embedding_dimension: number;
  timestamp: string;
}

/**
 * Senses telemetry state
 */
export interface SensesTelemetry {
  eventBuffer: NeuralPulseEvent[];
  reductionRate: number;
  lastEntropy: number;
  connected: boolean;
}

/**
 * Stomach telemetry state
 */
export interface StomachTelemetry {
  queueDepth: number;
  processingRate: number;
  vitals: SystemHealth;
  connected: boolean;
}

/**
 * Brain telemetry state
 */
export interface BrainTelemetry {
  nodeCount: number;
  avgConnectivity: number;
  embeddingDimension: number;
  connected: boolean;
}

/**
 * Unified system telemetry aggregate
 */
export interface SystemTelemetry {
  senses: SensesTelemetry;
  stomach: StomachTelemetry;
  brain: BrainTelemetry;
}

/**
 * Runtime configuration for the system
 */
export interface RuntimeConfig {
  entropy_threshold: number;
  embedding_model: string;
  percolation_similarity_threshold: number;
  metadata?: {
    biological_names?: {
      entropy_threshold: string;
      embedding_model: string;
      percolation_similarity_threshold: string;
    };
  };
}

/**
 * Configuration update request payload
 */
export interface ConfigUpdateRequest {
  entropy_threshold?: number;
  embedding_model?: string;
  percolation_similarity_threshold?: number;
}

/**
 * Configuration update response
 */
export interface ConfigUpdateResponse {
  status: string;
  updated_config: RuntimeConfig;
  message: string;
  note?: string;
}
