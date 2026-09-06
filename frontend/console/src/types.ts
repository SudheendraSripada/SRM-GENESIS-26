export type ScreenId = 'prompt' | 'analysing' | 'validating' | 'testing' | 'report';

export type NavTab = 'runs' | 'projects' | 'history';

export interface StepItem {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed';
  duration?: string;
  subtitle?: string;
  details?: {
    label: string;
    status: 'pending' | 'evaluating' | 'passed';
  }[];
}

export interface TelemetryData {
  activeVus: number;
  maxVus: number;
  p95Latency: number;
  p95LatencyDelta: number;
  rps: number;
  errorRate: number;
  durationSeconds: number;
}

export interface AssertionLog {
  id: string;
  timestamp: string;
  text: string;
  isAssertPass?: boolean;
  isActive?: boolean;
}

export interface DecisionStep {
  number: string;
  title: string;
  detail: string;
  highlighted?: boolean;
}

export interface RunData {
  id: string;
  name: string;
  query: string;
  target: string;
  env: string;
  cluster: string;
  startTime: string;
  duration: string;
  status: 'active' | 'completed' | 'failed' | 'queued';
  currentStepIndex: number;
  sustainableCapacity: number;
  targetSla: number;
  observedLatency: number;
  latencyMargin: number;
  steps: StepItem[];
  decisions: DecisionStep[];
  analystQuote: string;
  analystProse: string;
  evaluator: string;
  evaluatorTarget: string;
  compiledK6Script?: string;
  executionMetrics?: {
    requests: number;
    rps: number;
    avg_latency_ms: number;
    p50_ms: number;
    p90_ms: number;
    p95_ms: number;
    p99_ms: number;
    error_rate: number;
  };
  rawEvents?: Array<{
    event_id?: string;
    state: string;
    event_type: string;
    source: string;
    message: string;
    timestamp: string;
    details?: any;
  }>;
}

export interface ProjectItem {
  id: string;
  name: string;
  service: string;
  targetEndpoint: string;
  env: string;
  runsCount: number;
  lastRunStatus: 'passed' | 'failed' | 'running';
  lastRunDate: string;
  sustainableVus: number;
}
