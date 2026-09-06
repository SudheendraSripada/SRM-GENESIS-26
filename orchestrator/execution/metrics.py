"""
Deterministic Metrics Evaluation and Adaptive Boundary Search.
Extracts rigorous numerical telemetry from raw k6 execution summaries,
evaluates SLA thresholds mathematically, and drives adaptive search decisions.
Never invents metrics; all outputs strictly trace to execution data.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TestMetrics(BaseModel):
    """Normalized empirical telemetry measurements extracted from k6 summary."""
    requests: int = Field(default=0, ge=0, description="Total HTTP requests executed")
    rps: float = Field(default=0.0, ge=0.0, description="Measured average requests per second")
    avg_latency_ms: float = Field(default=0.0, ge=0.0, description="Mean response latency in ms")
    p50_ms: float = Field(default=0.0, ge=0.0, description="Median (50th percentile) latency in ms")
    p90_ms: float = Field(default=0.0, ge=0.0, description="90th percentile latency in ms")
    p95_ms: float = Field(default=0.0, ge=0.0, description="95th percentile latency in ms")
    p99_ms: float = Field(default=0.0, ge=0.0, description="99th percentile latency in ms")
    min_latency_ms: float = Field(default=0.0, ge=0.0, description="Minimum observed latency in ms")
    max_latency_ms: float = Field(default=0.0, ge=0.0, description="Maximum observed latency in ms")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of requests failed (0.0 to 1.0)")
    vus: int = Field(default=0, ge=0, description="Peak concurrent virtual users")
    iterations: int = Field(default=0, ge=0, description="Completed test iterations")
    checks_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Fraction of assertions passed")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Measured wall-clock test duration")


class ThresholdEvaluation(BaseModel):
    """Deterministic evaluation outcome for a single threshold criteria."""
    metric: str
    target_expression: str
    target_value: float
    actual_value: float
    operator: str
    passed: bool
    message: str


class DecisionResult(BaseModel):
    """Outcome of adaptive boundary search and run termination evaluation."""
    decision: str = Field(..., description="STOP_SATISFIED, STOP_FAILED, SCALE_UP, SCALE_DOWN, or CONTINUE_SEARCH")
    status: str = Field(..., description="PASS, FAIL, DEGRADED, or INCONCLUSIVE")
    reason: str = Field(..., description="Engineering explanation for the decision")
    current_vus: int = Field(default=0, description="Concurrencies tested in this cycle")
    target_vus: int = Field(default=0, description="Goal concurrency from test requirements")
    recommended_next_concurrency: Optional[int] = Field(default=None, description="Recommended concurrency for next iteration")
    breaking_point_vus: Optional[int] = Field(default=None, description="Estimated system saturation limit")
    threshold_results: List[ThresholdEvaluation] = Field(default_factory=list)


class MetricsEvaluator:
    """Deterministic parser and evaluator for k6 test metrics."""

    @classmethod
    def parse_summary(cls, summary_dict: Optional[Dict[str, Any]], duration_seconds: float = 0.0) -> TestMetrics:
        """Parses a raw k6 JSON summary into strongly typed TestMetrics."""
        if not summary_dict or not isinstance(summary_dict, dict):
            return TestMetrics(duration_seconds=duration_seconds)

        metrics_map = summary_dict.get("metrics", {})

        # Requests & Throughput
        http_reqs = metrics_map.get("http_reqs", {})
        requests = int(http_reqs.get("count", 0))
        rps = float(http_reqs.get("rate", 0.0))

        # Latency (http_req_duration)
        dur = metrics_map.get("http_req_duration", {})
        avg_ms = float(dur.get("avg", 0.0))
        p50_ms = float(dur.get("med", dur.get("p(50)", 0.0)))
        p90_ms = float(dur.get("p(90)", 0.0))
        p95_ms = float(dur.get("p(95)", 0.0))
        p99_ms = float(dur.get("p(99)", 0.0))
        min_ms = float(dur.get("min", 0.0))
        max_ms = float(dur.get("max", 0.0))

        # Error rate (http_req_failed)
        req_failed = metrics_map.get("http_req_failed", {})
        error_rate = float(req_failed.get("value", 0.0))
        if error_rate > 1.0:
            error_rate = error_rate / 100.0  # normalize if represented as percentage

        # Virtual users
        vus_metric = metrics_map.get("vus_max") or metrics_map.get("vus") or {}
        vus = int(vus_metric.get("value", vus_metric.get("max", 0)))

        # Iterations
        iters_metric = metrics_map.get("iterations", {})
        iterations = int(iters_metric.get("count", 0))

        # Checks
        checks_metric = metrics_map.get("checks", {})
        checks_pass_rate = float(checks_metric.get("value", 1.0))

        return TestMetrics(
            requests=requests,
            rps=round(rps, 2),
            avg_latency_ms=round(avg_ms, 2),
            p50_ms=round(p50_ms, 2),
            p90_ms=round(p90_ms, 2),
            p95_ms=round(p95_ms, 2),
            p99_ms=round(p99_ms, 2),
            min_latency_ms=round(min_ms, 2),
            max_latency_ms=round(max_ms, 2),
            error_rate=round(error_rate, 4),
            vus=vus,
            iterations=iterations,
            checks_pass_rate=round(checks_pass_rate, 4),
            duration_seconds=round(duration_seconds, 2),
        )

    @classmethod
    def evaluate_thresholds(
        cls,
        metrics: TestMetrics,
        thresholds: Union[Dict[str, Any], List[Any]],
    ) -> List[ThresholdEvaluation]:
        """
        Deterministically evaluates SLA threshold rules against actual measured metrics.
        Supports both k6 format ('p(95)<500') and agent threshold objects.
        """
        results: List[ThresholdEvaluation] = []

        if isinstance(thresholds, dict):
            # k6 options thresholds format: {"http_req_duration": ["p(95)<500", "p(99)<1000"], "http_req_failed": ["rate<0.01"]}
            for metric_name, rules in thresholds.items():
                rule_list = rules if isinstance(rules, list) else [rules]
                for expr in rule_list:
                    eval_item = cls._evaluate_k6_rule(metrics, metric_name, str(expr))
                    if eval_item:
                        results.append(eval_item)
        elif isinstance(thresholds, list):
            for item in thresholds:
                if isinstance(item, dict):
                    metric = item.get("metric", "p95")
                    target = float(item.get("target_value", item.get("target", 500)))
                    cond = item.get("condition", item.get("operator", "less_than"))
                    eval_item = cls._evaluate_simple_rule(metrics, metric, cond, target)
                    results.append(eval_item)
                elif hasattr(item, "metric") and hasattr(item, "target_value"):
                    # Pydantic ThresholdRule
                    cond = getattr(item.condition, "value", str(item.condition)) if hasattr(item, "condition") else "less_than"
                    eval_item = cls._evaluate_simple_rule(metrics, item.metric, cond, float(item.target_value))
                    results.append(eval_item)

        # Default fallback SLA checks if none specified
        if not results:
            results.append(cls._evaluate_simple_rule(metrics, "p95_latency", "less_than", 500.0))
            results.append(cls._evaluate_simple_rule(metrics, "error_rate", "less_than", 0.01))

        return results

    @classmethod
    def _evaluate_k6_rule(cls, metrics: TestMetrics, metric_name: str, expression: str) -> Optional[ThresholdEvaluation]:
        """Evaluates k6 rule string such as 'p(95)<500' or 'rate<=0.01'."""
        match = re.search(r"([<>=!]+)\s*([0-9.]+)", expression)
        if not match:
            return None

        op, val_str = match.groups()
        target_val = float(val_str)

        actual_val = 0.0
        display_metric = metric_name

        if "p(95)" in expression:
            actual_val = metrics.p95_ms
            display_metric = "p95_latency"
        elif "p(99)" in expression:
            actual_val = metrics.p99_ms
            display_metric = "p99_latency"
        elif "p(90)" in expression:
            actual_val = metrics.p90_ms
            display_metric = "p90_latency"
        elif "avg" in expression:
            actual_val = metrics.avg_latency_ms
            display_metric = "avg_latency"
        elif "rate" in expression or "failed" in metric_name:
            actual_val = metrics.error_rate
            display_metric = "error_rate"
            # If target was written as percentage (e.g. 1% -> 1.0 or 0.01)
            if target_val > 1.0:
                target_val = target_val / 100.0
        elif "rps" in expression:
            actual_val = metrics.rps
            display_metric = "throughput_rps"
        else:
            actual_val = metrics.p95_ms

        passed = cls._compare(actual_val, op, target_val)
        status_word = "PASSED" if passed else "VIOLATED"
        message = f"{display_metric} {op} {target_val} {status_word}: actual={actual_val}"

        return ThresholdEvaluation(
            metric=display_metric,
            target_expression=expression,
            target_value=target_val,
            actual_value=actual_val,
            operator=op,
            passed=passed,
            message=message,
        )

    @classmethod
    def _evaluate_simple_rule(
        cls,
        metrics: TestMetrics,
        metric_name: str,
        condition: str,
        target_value: float,
    ) -> ThresholdEvaluation:
        metric_lower = metric_name.lower()
        if "p95" in metric_lower:
            actual = metrics.p95_ms
        elif "p99" in metric_lower:
            actual = metrics.p99_ms
        elif "avg" in metric_lower:
            actual = metrics.avg_latency_ms
        elif "error" in metric_lower or "failed" in metric_lower:
            actual = metrics.error_rate
            if target_value > 1.0:
                target_value = target_value / 100.0
        elif "rps" in metric_lower or "throughput" in metric_lower:
            actual = metrics.rps
        else:
            actual = metrics.p95_ms

        cond_clean = condition.lower()
        if "less_than_or_equal" in cond_clean or cond_clean == "<=":
            op = "<="
        elif "less" in cond_clean or cond_clean == "<":
            op = "<"
        elif "greater_than_or_equal" in cond_clean or cond_clean == ">=":
            op = ">="
        elif "greater" in cond_clean or cond_clean == ">":
            op = ">"
        elif "equal" in cond_clean or cond_clean == "==":
            op = "=="
        else:
            op = "<="

        passed = cls._compare(actual, op, target_value)
        status_word = "PASSED" if passed else "VIOLATED"
        expr = f"{metric_name} {op} {target_value}"
        msg = f"{metric_name} ({actual}) {op} {target_value} -> {status_word}"

        return ThresholdEvaluation(
            metric=metric_name,
            target_expression=expr,
            target_value=target_value,
            actual_value=actual,
            operator=op,
            passed=passed,
            message=msg,
        )

    @staticmethod
    def _compare(actual: float, op: str, target: float) -> bool:
        if op == "<":
            return actual < target
        elif op == "<=":
            return actual <= target
        elif op == ">":
            return actual > target
        elif op == ">=":
            return actual >= target
        elif op in ("==", "="):
            return abs(actual - target) < 1e-6
        return False

    @classmethod
    def evaluate_decision(
        cls,
        metrics: TestMetrics,
        threshold_evals: List[ThresholdEvaluation],
        current_vus: int,
        target_vus: int,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> DecisionResult:
        """
        Deterministic adaptive boundary search decision.
        Evaluates SLA compliance and dictates whether to stop or search next concurrency.
        """
        all_passed = all(t.passed for t in threshold_evals) if threshold_evals else True
        error_rate = metrics.error_rate

        if all_passed:
            if current_vus >= target_vus or current_vus == 0:
                return DecisionResult(
                    decision="STOP_SATISFIED",
                    status="PASS",
                    reason=f"All SLA thresholds satisfied at target concurrency ({current_vus} VUs).",
                    current_vus=current_vus,
                    target_vus=target_vus,
                    recommended_next_concurrency=None,
                    threshold_results=threshold_evals,
                )
            else:
                next_vus = min(target_vus, int(current_vus * 1.5))
                return DecisionResult(
                    decision="SCALE_UP",
                    status="PASS",
                    reason=f"SLA satisfied at {current_vus} VUs; scaling concurrency towards target {target_vus} VUs.",
                    current_vus=current_vus,
                    target_vus=target_vus,
                    recommended_next_concurrency=next_vus,
                    threshold_results=threshold_evals,
                )

        # One or more thresholds failed
        if error_rate >= 0.10:
            status = "FAIL"
            decision = "STOP_FAILED"
            reason = f"System saturated: high error rate ({error_rate * 100:.1f}%) observed at {current_vus} VUs."
            breaking_point = current_vus
        elif any(not t.passed and "p95" in t.metric for t in threshold_evals):
            status = "DEGRADED"
            # If we were searching boundaries, binary search downwards
            if current_vus > 10:
                next_vus = max(1, current_vus // 2)
                decision = "SCALE_DOWN"
                reason = f"Latency degradation observed at {current_vus} VUs; decreasing concurrency to test {next_vus} VUs."
                breaking_point = current_vus
            else:
                decision = "STOP_FAILED"
                reason = f"Latency threshold violated even at baseline concurrency ({current_vus} VUs)."
                breaking_point = current_vus
                next_vus = None
        else:
            status = "FAIL"
            decision = "STOP_FAILED"
            reason = f"Threshold criteria violated at {current_vus} VUs."
            breaking_point = current_vus
            next_vus = None

        return DecisionResult(
            decision=decision,
            status=status,
            reason=reason,
            current_vus=current_vus,
            target_vus=target_vus,
            recommended_next_concurrency=next_vus,
            breaking_point_vus=breaking_point,
            threshold_results=threshold_evals,
        )

