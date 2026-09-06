"""
Tests for K6Runner and MetricsEvaluator.
Verifies real subprocess execution using the local k6 CLI binary,
deterministic metrics parsing, threshold evaluations, and boundary search.
"""

import asyncio
import pytest
from orchestrator.execution.k6_runner import K6Runner, K6ExecutionResult
from orchestrator.execution.metrics import (
    MetricsEvaluator,
    TestMetrics as MetricsData,
    DecisionResult,
)


@pytest.mark.anyio
async def test_k6_runner_executes_real_k6_script():
    runner = K6Runner()
    # Simple valid ES6 k6 test script
    script = """
    import { check } from 'k6';

    export const options = {
      vus: 1,
      duration: '1s',
    };

    export default function () {
      check(1, {
        'truthy check': (x) => x === 1,
      });
    }
    """

    events = []
    async def on_event(event_type, msg, details):
        events.append((event_type, msg))

    res: K6ExecutionResult = await runner.execute(
        run_id="test_run_real_k6",
        script_content=script,
        timeout_seconds=10,
        event_callback=on_event,
    )

    assert res.status == "COMPLETED"
    assert res.exit_code == 0
    assert res.summary is not None
    assert "metrics" in res.summary
    assert res.is_mock_simulated is False
    assert len(events) >= 2


@pytest.mark.anyio
async def test_k6_runner_timeout_handling():
    runner = K6Runner()
    # Script intended to run for 10s, but we set timeout to 1s
    script = """
    import { sleep } from 'k6';
    export const options = { vus: 1, duration: '10s' };
    export default function () {
      sleep(1);
    }
    """
    res = await runner.execute(
        run_id="test_run_timeout",
        script_content=script,
        timeout_seconds=1,
    )
    assert res.status == "TIMEOUT"
    assert "safety limit" in (res.error_message or "")


@pytest.mark.anyio
async def test_k6_runner_mock_fallback_on_unresolvable_domain():
    runner = K6Runner()
    script = """
    import http from 'k6/http';
    export const options = { vus: 1, duration: '1s' };
    export default function () {
      http.get('http://staging-ecom.local/api/test');
    }
    """
    res = await runner.execute(
        run_id="test_run_mock_fallback",
        script_content=script,
        timeout_seconds=5,
        mock_fallback=True,
    )
    assert res.status == "COMPLETED"
    assert res.is_mock_simulated is True
    assert res.summary is not None
    assert "http_req_duration" in res.summary["metrics"]


def test_metrics_evaluator_parses_summary():
    raw_summary = {
        "metrics": {
            "http_reqs": {"count": 1000, "rate": 50.0},
            "http_req_duration": {
                "avg": 120.5,
                "min": 20.0,
                "med": 110.0,
                "max": 350.0,
                "p(90)": 180.0,
                "p(95)": 240.0,
                "p(99)": 310.0,
            },
            "http_req_failed": {"passes": 5, "fails": 995, "value": 0.005},
            "vus": {"value": 50},
            "iterations": {"count": 1000},
            "checks": {"value": 0.995},
        }
    }

    metrics: MetricsData = MetricsEvaluator.parse_summary(raw_summary, duration_seconds=20.0)

    assert metrics.requests == 1000
    assert metrics.rps == 50.0
    assert metrics.p95_ms == 240.0
    assert metrics.p99_ms == 310.0
    assert metrics.error_rate == 0.005
    assert metrics.vus == 50


def test_threshold_evaluator_and_decision():
    metrics = MetricsData(
        requests=5000,
        rps=100.0,
        avg_latency_ms=150.0,
        p50_ms=130.0,
        p90_ms=210.0,
        p95_ms=280.0,
        p99_ms=420.0,
        error_rate=0.002,
        vus=500,
        iterations=5000,
        duration_seconds=50.0,
    )

    threshold_rules = {
        "http_req_duration": ["p(95)<500", "p(99)<1000"],
        "http_req_failed": ["rate<0.01"],
    }

    evals = MetricsEvaluator.evaluate_thresholds(metrics, threshold_rules)
    assert len(evals) == 3
    assert all(e.passed for e in evals)

    # Decision evaluation when all passed and target concurrency achieved
    decision: DecisionResult = MetricsEvaluator.evaluate_decision(
        metrics=metrics,
        threshold_evals=evals,
        current_vus=500,
        target_vus=500,
    )
    assert decision.decision == "STOP_SATISFIED"
    assert decision.status == "PASS"

    # Decision evaluation when degraded
    degraded_metrics = metrics.model_copy(update={"p95_ms": 750.0})
    degraded_evals = MetricsEvaluator.evaluate_thresholds(degraded_metrics, threshold_rules)
    assert any(not e.passed for e in degraded_evals)

    degraded_decision = MetricsEvaluator.evaluate_decision(
        metrics=degraded_metrics,
        threshold_evals=degraded_evals,
        current_vus=500,
        target_vus=500,
    )
    assert degraded_decision.status == "DEGRADED"
    assert degraded_decision.decision == "SCALE_DOWN"
