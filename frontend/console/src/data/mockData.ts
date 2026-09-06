import { StepItem, DecisionStep, ProjectItem, RunData } from '../types';

export const DEFAULT_RUN_QUERY =
  'Test fuzzy authentication flows across staging api.v2 endpoints with concurrency limit 50 and observe idempotency keys';

export const INITIAL_STEPS: StepItem[] = [
  {
    id: 'analysing',
    name: 'Analysing',
    status: 'completed',
    duration: '1.2s',
    subtitle: 'Mapping endpoint schema & auth headers...',
  },
  {
    id: 'building-plan',
    name: 'Building Plan',
    status: 'completed',
    duration: '3.4s',
    subtitle: 'Queued',
  },
  {
    id: 'validating',
    name: 'Validating',
    status: 'completed',
    duration: '0.8s',
    details: [
      { label: 'Intent schema', status: 'passed' },
      { label: 'Target allowlist', status: 'passed' },
      { label: 'Load bounds', status: 'evaluating' },
      { label: 'Payload validity', status: 'pending' },
      { label: 'Execution policy', status: 'pending' },
    ],
  },
  {
    id: 'building-test',
    name: 'Building Test',
    status: 'completed',
    duration: '2.1s',
  },
  {
    id: 'testing',
    name: 'Testing',
    status: 'active',
  },
  {
    id: 'summarizing',
    name: 'Summarizing',
    status: 'pending',
  },
  {
    id: 'building-report',
    name: 'Building Report',
    status: 'pending',
  },
];

export const INITIAL_DECISIONS: DecisionStep[] = [
  {
    number: '01',
    title: 'Started at 100 VUs baseline load across 6 staging API targets',
    detail: 'Initial probe: warm-up period 10.0s · connection pool stable at 48 sockets',
  },
  {
    number: '02',
    title: 'Escalated to 300 VUs; p95 latency held steady at 412ms with 0.1% idempotency retries',
    detail: 'Step increment +200 VUs · response codes: 99.89% 200 OK · no socket starvation detected',
  },
  {
    number: '03',
    title: 'Binary search converged at 350 VUs — load boundary identified before latency ceiling breach',
    detail: 'Probe delta reached tolerance (±10 VUs) · halted escalation to preserve environment hygiene',
    highlighted: true,
  },
];

export const INITIAL_ASSERTION_LOGS = [
  {
    id: 'log-1',
    timestamp: '14:32:02.109',
    text: 'POST /v2/auth/token concurrency_slot=14 idempotency_key=8f9a2e -> 200 OK (384ms)',
  },
  {
    id: 'log-2',
    timestamp: '14:32:02.342',
    text: 'POST /v2/auth/token concurrency_slot=32 idempotency_key=8f9a2e (replay) -> 200 OK [CACHED] (28ms)',
  },
  {
    id: 'log-3',
    timestamp: '14:32:02.781',
    text: 'ASSERT PASS: Idempotency invariant holds under state variance',
    isAssertPass: true,
  },
  {
    id: 'log-4',
    timestamp: '14:32:03.011',
    text: 'POST /v2/auth/introspect fuzzy_payload=0x7f..af34',
    isActive: true,
  },
];

export const MOCK_K6_SCRIPT = `import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Trend, Counter } from 'k6/metrics';

// Synthesized autonomous test suite: run_088f12a9_auth_fuzz
const p95Trend = new Trend('p95_auth_latency');
const idempotencyViolations = new Counter('idempotency_violations');

export const options = {
  scenarios: {
    binary_capacity_probe: {
      executor: 'ramping-vus',
      startVUs: 50,
      stages: [
        { duration: '15s', target: 100 }, // baseline warm-up
        { duration: '20s', target: 300 }, // high concurrency spike
        { duration: '25s', target: 350 }, // capacity boundary probe
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    'http_req_duration': ['p(95)<500'], // Strict SLA ceiling: 500ms
    'http_req_failed': ['rate<0.01'],    // Error tolerance < 1%
    'idempotency_violations': ['count==0'],
  },
};

const BASE_URL = 'https://staging.api.v2.internal';

export default function () {
  const idempotencyKey = 'idemp_' + Math.random().toString(36).substring(2, 10);
  const payload = JSON.stringify({
    client_id: 'synthetics-agent-v2.4',
    scope: 'openid offline_access internal_write',
    fuzzy_seed: Math.floor(Math.random() * 0xffffffff).toString(16),
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-Idempotency-Key': idempotencyKey,
      'X-Cluster-Origin': 'prod-eu-west-1',
    },
  };

  group('Auth Token Invariance Check', function () {
    const res1 = http.post(\`\${BASE_URL}/v2/auth/token\`, payload, params);
    check(res1, {
      'initial response is 200': (r) => r.status === 200,
      'latency within SLA': (r) => r.timings.duration < 500,
    });
    p95Trend.add(res1.timings.duration);

    // Immediate replay check with same idempotency key
    const res2 = http.post(\`\${BASE_URL}/v2/auth/token\`, payload, params);
    const isCachedReplay = res2.status === 200 && res2.body === res1.body;
    
    if (!isCachedReplay) {
      idempotencyViolations.add(1);
    }

    check(res2, {
      'replay matched idempotency fingerprint': () => isCachedReplay,
      'cached replay returned < 50ms': (r) => r.timings.duration < 50,
    });
  });

  sleep(0.1);
}`;

export const MOCK_EXECUTION_TRACE = [
  {
    id: 'span-0',
    service: 'api-gateway',
    operation: 'POST /v2/auth/token',
    duration: '384ms',
    durationMs: 384,
    status: '200 OK',
    offsetMs: 0,
    tags: { 'http.status_code': 200, 'idempotency.hit': false, 'client': 'agent-300' },
  },
  {
    id: 'span-1',
    service: 'auth-service',
    operation: 'middleware.validate_schema',
    duration: '12ms',
    durationMs: 12,
    status: 'OK',
    offsetMs: 14,
    tags: { 'schema.version': '2.4.0', 'eval': 'pass' },
  },
  {
    id: 'span-2',
    service: 'redis-cache',
    operation: 'GET idemp:8f9a2e',
    duration: '4ms',
    durationMs: 4,
    status: 'MISS',
    offsetMs: 28,
    tags: { 'cache.cluster': 'eu-west-1-redis-primary' },
  },
  {
    id: 'span-3',
    service: 'vault-signer',
    operation: 'kms.sign_asymmetric_jwt',
    duration: '298ms',
    durationMs: 298,
    status: '200 OK',
    offsetMs: 34,
    tags: { 'key.algorithm': 'RS256', 'key.id': 'prod_sign_2026' },
  },
  {
    id: 'span-4',
    service: 'redis-cache',
    operation: 'SETEX idemp:8f9a2e 300s',
    duration: '6ms',
    durationMs: 6,
    status: 'OK',
    offsetMs: 336,
    tags: { 'ttl': '300s' },
  },
  {
    id: 'span-5',
    service: 'api-gateway',
    operation: 'POST /v2/auth/token [REPLAY]',
    duration: '28ms',
    durationMs: 28,
    status: '200 OK (CACHED)',
    offsetMs: 390,
    tags: { 'idempotency.hit': true, 'source': 'redis' },
  },
];

export const MOCK_PROJECTS: ProjectItem[] = [
  {
    id: 'proj-1',
    name: 'auth-service-staging-eu',
    service: 'Authentication Core',
    targetEndpoint: 'api.v2.internal/v2/auth',
    env: 'staging',
    runsCount: 38,
    lastRunStatus: 'passed',
    lastRunDate: 'Just now',
    sustainableVus: 350,
  },
  {
    id: 'proj-2',
    name: 'checkout-orchestrator',
    service: 'Payment Webhooks',
    targetEndpoint: 'checkout.internal/webhooks',
    env: 'staging',
    runsCount: 19,
    lastRunStatus: 'passed',
    lastRunDate: '3 hours ago',
    sustainableVus: 520,
  },
  {
    id: 'proj-3',
    name: 'order-settlement-engine',
    service: 'Ledger & Settlement',
    targetEndpoint: 'ledger.v1.internal/settle',
    env: 'canary',
    runsCount: 14,
    lastRunStatus: 'passed',
    lastRunDate: 'Yesterday',
    sustainableVus: 280,
  },
  {
    id: 'proj-4',
    name: 'notification-dispatch',
    service: 'Push & SMS Broker',
    targetEndpoint: 'events.v2.internal/publish',
    env: 'staging',
    runsCount: 52,
    lastRunStatus: 'passed',
    lastRunDate: '2 days ago',
    sustainableVus: 840,
  },
];

export const MOCK_HISTORY_RUNS: RunData[] = [
  {
    id: 'run_088f12a9_auth_fuzz',
    name: 'Fuzzy Auth & Concurrency Boundary',
    query: DEFAULT_RUN_QUERY,
    target: 'api.v2.internal',
    env: 'staging',
    cluster: 'prod-eu-west-1',
    startTime: 'Today, 14:31',
    duration: '51.3s',
    status: 'completed',
    currentStepIndex: 6,
    sustainableCapacity: 350,
    targetSla: 500,
    observedLatency: 438,
    latencyMargin: -62,
    steps: INITIAL_STEPS,
    decisions: INITIAL_DECISIONS,
    analystQuote:
      'Under synthetic auth fuzzing, api.v2 endpoints comfortably absorbed concurrent burst traffic up to 350 virtual users while remaining safely within the established 500ms p95 SLA window.',
    analystProse:
      'Beyond 365 VUs, Redis token cache eviction pressure caused upstream introspection times to spike past 620ms. The system has safely converged on 350 VUs as the recommended production throttling threshold. Further capacity gains will require transitioning the token validation layer from remote introspection to distributed asymmetric JWT verification.',
    evaluator: 'Synthetics Agent v2.4',
    evaluatorTarget: 'auth-service-staging-eu',
  },
  {
    id: 'run_77a23c14_payment_spike',
    name: 'Checkout Webhook Invariance Under Load',
    query: 'Simulate concurrent load spikes on checkout webhook endpoints up to 10k rps',
    target: 'checkout.internal',
    env: 'staging',
    cluster: 'prod-eu-west-1',
    startTime: 'Today, 11:15',
    duration: '1m 24s',
    status: 'completed',
    currentStepIndex: 6,
    sustainableCapacity: 520,
    targetSla: 250,
    observedLatency: 218,
    latencyMargin: -32,
    steps: INITIAL_STEPS,
    decisions: INITIAL_DECISIONS,
    analystQuote:
      'Zero double-capture events detected across 12,000 synthetic retry loops with duplicate idempotency keys.',
    analystProse:
      'Database row locking on order status updates held steady without deadlocks. Transaction serialization level maintained ACID guarantees under synthetic burst testing.',
    evaluator: 'Synthetics Agent v2.4',
    evaluatorTarget: 'checkout-orchestrator',
  },
  {
    id: 'run_3f91b002_idemp_rollback',
    name: 'Payment Settlement Failure State Rollback',
    query: 'Verify state rollbacks and idempotency keys on payment settlement failures',
    target: 'ledger.v1.internal',
    env: 'canary',
    cluster: 'prod-us-east-1',
    startTime: 'Yesterday, 17:40',
    duration: '44.8s',
    status: 'completed',
    currentStepIndex: 6,
    sustainableCapacity: 280,
    targetSla: 400,
    observedLatency: 342,
    latencyMargin: -58,
    steps: INITIAL_STEPS,
    decisions: INITIAL_DECISIONS,
    analystQuote:
      'Simulated upstream network partitions during 2-phase commit resulted in clean state reversions.',
    analystProse:
      'Compensating transactions were triggered within 40ms of simulated timeout. No orphaned ledger entries were discovered during post-test reconciliation.',
    evaluator: 'Synthetics Agent v2.4',
    evaluatorTarget: 'order-settlement-engine',
  },
];
