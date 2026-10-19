export interface AgentStatus {
  role: 'coder' | 'orchestrator';
  id: string;
  running: boolean;
  currentTask: string | null;
  tasksCompleted: number;
  lastResult: string | null;
}

export interface TaskMessage {
  id: string;
  from: string;
  to: string;
  description: string;
  timestamp: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface MCPResource {
  uri: string;
  name: string;
  description: string;
}

export interface RAGDocument {
  id: string;
  content: string;
  metadata: Record<string, string>;
  score?: number;
}

export interface TrainingExample {
  instruction: string;
  input: string;
  output: string;
}

export interface FineTuneConfig {
  baseModel: string;
  numEpochs: number;
  batchSize: number;
  learningRate: number;
}

export interface MonitorSummary {
  uptimeSeconds: number;
  requests: {
    total: number;
    success: number;
    failed: number;
    successRate: number;
  };
  latency: {
    count: number;
    min: number;
    max: number;
    mean: number;
    p50: number;
    p95: number;
  };
  llmCalls: number;
}

export interface BenchmarkResult {
  name: string;
  success: boolean;
  duration: number;
  score: number;
  details: Record<string, unknown>;
}
