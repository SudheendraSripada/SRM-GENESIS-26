"""
Orchestrator Execution Engine.
Manages the run lifecycle state machine:
CREATED -> ANALYSING -> PLANNING -> CRITIC_REVIEW -> VALIDATING -> BUILDING ->
EXECUTING -> ANALYSING_RESULTS -> DECIDING_NEXT_TEST -> SUMMARIZING -> REPORTING -> COMPLETED
with explicit terminal states (FAILED, BLOCKED, CANCELLED, TIMEOUT).
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, Optional
import httpx

from orchestrator.models import AgentEvent, RunState
from orchestrator.db import Database
from orchestrator.event_bus import EventBus
from orchestrator.adapters.spec_adapter import (
    adapt_specification,
    build_safety_policy,
)

# Agent models and fixtures
from performance_testing_ai.pipeline import PerformanceTestingPipeline
from performance_testing_ai.agents.critic_agent import evaluate_safety
from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_REQUIREMENT_SPEC,
    MOCK_PERFORMANCE_PLAN,
    MOCK_TEST_DATA_PLAN,
    MOCK_TEST_SPECIFICATION,
    MOCK_EXECUTION_RESULT,
    MOCK_ANALYSIS_RESULT,
)

# Validator models
from app.engine.pipeline_orchestrator import PipelineOrchestrator
from app.models.validation_result import PipelineStatus

# Execution and Metrics
from orchestrator.execution.k6_runner import K6Runner
from orchestrator.execution.metrics import MetricsEvaluator
from performance_testing_ai.models.execution_result import (
    ExecutionResult,
    ExecutionMetrics,
    ExecutionStatus,
    ThresholdResult,
)
from performance_testing_ai.models.analysis_result import (
    AnalysisResult,
    Observation,
    Hypothesis,
    BottleneckIndicator,
    SlaAssessment,
    SlaStatus,
)


class OrchestratorEngine:
    def __init__(
        self,
        db: Database,
        event_bus: EventBus,
        validator_url: str = "http://127.0.0.1:8000",
        k6_path: Optional[str] = None,
    ):
        self.db = db
        self.event_bus = event_bus
        self.validator_url = os.getenv("VALIDATOR_URL", validator_url).rstrip("/")
        self.k6_runner = K6Runner(k6_path=k6_path)
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def emit_event(
        self,
        run_id: str,
        state: RunState,
        event_type: str,
        message: str,
        source: str = "orchestrator",
        details: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        """Records and broadcasts an AgentEvent."""
        event = AgentEvent(
            run_id=run_id,
            state=state,
            event_type=event_type,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat(),
            message=message,
            details=details or {},
        )
        await self.db.save_event(event)
        await self.event_bus.publish(event)
        return event

    async def cancel_run(self, run_id: str) -> bool:
        """Cancels an in-progress run."""
        await self.k6_runner.cancel(run_id)
        task = self._running_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            await self.db.update_run_state(run_id, RunState.CANCELLED, "Run cancelled by user")
            await self.emit_event(
                run_id=run_id,
                state=RunState.CANCELLED,
                event_type="run_cancelled",
                message="Run was cancelled by user request",
            )
            return True
        return False

    def start_run(self, run_id: str, prompt: str, mock_mode: bool = True) -> asyncio.Task:
        """Launches the state machine execution as a background asyncio task."""
        task = asyncio.create_task(self._execute_run(run_id, prompt, mock_mode))
        self._running_tasks[run_id] = task
        task.add_done_callback(lambda t: self._running_tasks.pop(run_id, None))
        return task

    async def _execute_run(self, run_id: str, prompt: str, mock_mode: bool = True):
        """Executes the full pipeline state machine."""
        try:
            # -----------------------------------------------------------------
            # State: CREATED
            # -----------------------------------------------------------------
            await self.emit_event(
                run_id=run_id,
                state=RunState.CREATED,
                event_type="run_initialized",
                message=f"Initialized run for prompt: '{prompt[:80]}...'",
                details={"mock_mode": mock_mode},
            )

            # -----------------------------------------------------------------
            # State: ANALYSING (Requirement Analyst Agent)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.ANALYSING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.ANALYSING,
                event_type="stage_started",
                source="requirement_analyst",
                message="Requirement Analyst: Extracting target application, endpoints, and SLAs from prompt.",
            )

            # Execute pipeline
            pipeline = PerformanceTestingPipeline(mock_mode=mock_mode)
            # In mock mode this returns synchronously
            context = pipeline.run(user_request=prompt)

            req_spec = context.requirement_spec or MOCK_REQUIREMENT_SPEC
            await self.db.save_artifact(run_id, "requirement_spec", req_spec.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.ANALYSING,
                event_type="stage_completed",
                source="requirement_analyst",
                message=(
                    f"Requirement Analyst: Identified target '{req_spec.target_application}' "
                    f"with {req_spec.expected_users} VUs and {len(req_spec.thresholds)} SLA thresholds."
                ),
                details={"target_application": req_spec.target_application, "vus": req_spec.expected_users},
            )

            # -----------------------------------------------------------------
            # State: PLANNING (Performance Planner & Test Data Agents)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.PLANNING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.PLANNING,
                event_type="stage_started",
                source="performance_planner",
                message="Performance Planner: Constructing ramp-up, steady-state, and ramp-down execution stages.",
            )

            plan = context.performance_plan or MOCK_PERFORMANCE_PLAN
            await self.db.save_artifact(run_id, "performance_plan", plan.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.PLANNING,
                event_type="stage_completed",
                source="performance_planner",
                message=f"Performance Planner: Generated plan with {len(plan.stages)} stages, peak {plan.target_vus} VUs.",
                details={"stages_count": len(plan.stages), "peak_vus": plan.target_vus},
            )

            # Test Data Agent stage
            test_data_plan = context.test_data_plan or MOCK_TEST_DATA_PLAN
            await self.db.save_artifact(run_id, "test_data_plan", test_data_plan.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.PLANNING,
                event_type="test_data_plan_generated",
                source="test_data_agent",
                message=f"Test Data Agent: Identified datasets ({len(test_data_plan.datasets_needed)}) and parameterization rules.",
                details={"datasets": [d.name for d in test_data_plan.datasets_needed]},
            )

            # Workload Builder stage
            test_spec = context.test_specification or MOCK_TEST_SPECIFICATION
            await self.db.save_artifact(run_id, "test_specification", test_spec.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.PLANNING,
                event_type="test_specification_built",
                source="workload_builder",
                message=f"Workload Builder: Generated TestSpecification '{test_spec.test_name}'.",
                details={"test_id": test_spec.test_id, "steps_count": len(test_spec.request_sequence)},
            )

            # -----------------------------------------------------------------
            # State: CRITIC_REVIEW (Critic / Safety Agent)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.CRITIC_REVIEW)
            await self.emit_event(
                run_id=run_id,
                state=RunState.CRITIC_REVIEW,
                event_type="stage_started",
                source="critic_agent",
                message="Critic / Safety Agent: Evaluating safety bounds, target authorization, and load ceilings.",
            )

            critic_res = evaluate_safety(test_spec)
            await self.db.save_artifact(run_id, "critic_result", critic_res.model_dump())

            is_approved = critic_res.approved and critic_res.risk_level.value != "critical"

            if not is_approved:
                rejection_msg = "; ".join(critic_res.issues) if critic_res.issues else critic_res.review_summary
                await self.db.update_run_state(
                    run_id,
                    RunState.BLOCKED,
                    error_message=f"Safety Critic rejected specification: {rejection_msg}",
                )
                await self.emit_event(
                    run_id=run_id,
                    state=RunState.BLOCKED,
                    event_type="critic_blocked",
                    source="critic_agent",
                    message=f"BLOCKED: Safety Critic rejected specification: {rejection_msg}",
                    details={"critic_result": critic_res.model_dump()},
                )
                return  # Hard stop! Never silently retry.

            await self.emit_event(
                run_id=run_id,
                state=RunState.CRITIC_REVIEW,
                event_type="stage_completed",
                source="critic_agent",
                message=f"Critic / Safety Agent approved specification with risk level: {critic_res.risk_level.value}.",
                details={"risk_level": critic_res.risk_level.value},
            )

            # -----------------------------------------------------------------
            # State: VALIDATING (Schema Adapter + Validator Service)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.VALIDATING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.VALIDATING,
                event_type="stage_started",
                source="validator",
                message="Validator: Adapting specification and executing 8-stage progressive verification pipeline.",
            )

            # Adapt specification
            adaptation = adapt_specification(test_spec, test_data_plan)
            # Forward any adaptation events (e.g. multi-step simplification)
            for evt in adaptation.events:
                await self.emit_event(
                    run_id=run_id,
                    state=RunState.VALIDATING,
                    event_type=evt.event_type,
                    source=evt.source,
                    message=evt.message,
                    details=evt.details,
                )

            adapted_dict = adaptation.to_dict()
            await self.db.save_artifact(run_id, "adapted_test_spec", adapted_dict)

            # Send to validator service (HTTP POST /api/v1/validate) with direct fallback
            val_result_dict = await self._call_validator(test_spec, adapted_dict)
            await self.db.save_artifact(run_id, "validation_result", val_result_dict)

            val_status = val_result_dict.get("status")
            if val_status != "VALID":
                errs = val_result_dict.get("errors", [])
                err_msgs = [e.get("message", "Validation error") for e in errs]
                err_summary = "; ".join(err_msgs) if err_msgs else "Validation rejected"
                await self.db.update_run_state(
                    run_id,
                    RunState.BLOCKED,
                    error_message=f"Validator rejected specification: {err_summary}",
                )
                await self.emit_event(
                    run_id=run_id,
                    state=RunState.BLOCKED,
                    event_type="validation_blocked",
                    source="validator",
                    message=f"BLOCKED: Validator rejected specification: {err_summary}",
                    details={"errors": errs, "score": val_result_dict.get("validation_score", 0)},
                )
                return  # Hard stop! Never silently retry.

            await self.emit_event(
                run_id=run_id,
                state=RunState.VALIDATING,
                event_type="stage_completed",
                source="validator",
                message=f"Validator: All 8 progressive verification stages PASSED (Score: {val_result_dict.get('validation_score')}/100).",
                details={"score": val_result_dict.get("validation_score"), "stages": val_result_dict.get("stages")},
            )

            # -----------------------------------------------------------------
            # State: BUILDING (k6 ES6 Script Compilation)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.BUILDING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.BUILDING,
                event_type="stage_started",
                source="k6_compiler",
                message="Building: Compiling validated Canonical Spec IR into executable k6 ES6 script.",
            )

            compiled_script = val_result_dict.get("compiled_k6_script")
            if not compiled_script:
                compiled_script = await self._call_compiler(val_result_dict.get("normalized_spec") or adapted_dict)

            await self.db.save_artifact(run_id, "compiled_k6_script", compiled_script)
            await self.emit_event(
                run_id=run_id,
                state=RunState.BUILDING,
                event_type="stage_completed",
                source="k6_compiler",
                message="Building: Deterministic k6 script compiled successfully.",
                details={"script_preview": compiled_script[:200] + "..."},
            )

            # -----------------------------------------------------------------
            # State: EXECUTING (k6 Execution Engine)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.EXECUTING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.EXECUTING,
                event_type="stage_started",
                source="k6_engine",
                message="Executing: Launching k6 performance execution via verified local binary.",
            )

            async def _on_k6_event(event_type: str, message: str, details: Dict[str, Any]):
                await self.emit_event(
                    run_id=run_id,
                    state=RunState.EXECUTING,
                    event_type=event_type,
                    source="k6_engine",
                    message=f"Executing: {message}",
                    details=details,
                )

            spec_duration = adapted_dict.get("load", {}).get("duration_seconds", 30)
            duration_override = "2s" if mock_mode else None
            timeout_limit = 10 if mock_mode else max(spec_duration + 20, 60)

            k6_res = await self.k6_runner.execute(
                run_id=run_id,
                script_content=compiled_script,
                timeout_seconds=timeout_limit,
                duration_override=duration_override,
                mock_fallback=mock_mode,
                event_callback=_on_k6_event,
            )

            if k6_res.status in ("FAILED", "TIMEOUT", "CANCELLED") and not k6_res.summary:
                fail_msg = k6_res.error_message or f"k6 execution failed with status {k6_res.status}"
                await self.db.update_run_state(run_id, RunState.FAILED, error_message=fail_msg)
                await self.emit_event(
                    run_id=run_id,
                    state=RunState.FAILED,
                    event_type="execution_failed",
                    source="k6_engine",
                    message=f"FAILED: {fail_msg}",
                    details={"stdout": k6_res.stdout[:500], "stderr": k6_res.stderr[:500]},
                )
                return

            # Extract deterministic telemetry directly from k6 summary
            measured_metrics = MetricsEvaluator.parse_summary(
                k6_res.summary,
                duration_seconds=k6_res.duration_seconds,
            )

            # Evaluate thresholds against measured numbers
            threshold_evals = MetricsEvaluator.evaluate_thresholds(
                measured_metrics,
                test_spec.thresholds,
            )

            exec_status = (
                ExecutionStatus.SUCCESS
                if all(t.passed for t in threshold_evals)
                else ExecutionStatus.FAILED
            )

            exec_res = ExecutionResult(
                test_id=test_spec.test_id,
                status=exec_status,
                metrics=ExecutionMetrics(
                    requests=measured_metrics.requests,
                    rps=measured_metrics.rps,
                    avg_latency_ms=measured_metrics.avg_latency_ms,
                    p95_ms=measured_metrics.p95_ms,
                    p99_ms=measured_metrics.p99_ms,
                    error_rate=measured_metrics.error_rate,
                    iterations=measured_metrics.iterations,
                ),
                thresholds=[
                    ThresholdResult(
                        metric=t.metric,
                        threshold_expression=t.target_expression,
                        actual_value=t.actual_value,
                        passed=t.passed,
                    )
                    for t in threshold_evals
                ],
                raw_summary_reference=None,
            )

            await self.db.save_artifact(run_id, "execution_result", exec_res.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.EXECUTING,
                event_type="stage_completed",
                source="k6_engine",
                message=(
                    f"Executing: k6 completed. Processed {measured_metrics.requests} requests, "
                    f"throughput {measured_metrics.rps} rps, p95 {measured_metrics.p95_ms}ms, "
                    f"error rate {measured_metrics.error_rate * 100:.2f}%."
                ),
                details=measured_metrics.model_dump(),
            )

            # -----------------------------------------------------------------
            # State: ANALYSING_RESULTS (Performance Analyst Agent 6)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.ANALYSING_RESULTS)
            await self.emit_event(
                run_id=run_id,
                state=RunState.ANALYSING_RESULTS,
                event_type="stage_started",
                source="performance_analyst",
                message="Performance Analyst: Analyzing execution metrics against SLA thresholds and identifying bottlenecks.",
            )

            # Ground analyst findings strictly in measured metrics
            sla_assessments = [
                SlaAssessment(
                    metric=t.metric,
                    target_threshold=t.target_expression,
                    actual_value=f"{t.actual_value:.2f}",
                    status=SlaStatus.COMPLIANT if t.passed else SlaStatus.VIOLATED,
                    details=t.message,
                )
                for t in threshold_evals
            ]

            obs = [
                Observation(
                    metric_or_signal="Throughput & Requests",
                    observed_fact=f"Processed {measured_metrics.requests} total requests at {measured_metrics.rps} req/sec.",
                    evidence_source="k6.http_reqs",
                ),
                Observation(
                    metric_or_signal="Response Latency Profile",
                    observed_fact=(
                        f"Mean latency {measured_metrics.avg_latency_ms}ms, p50 {measured_metrics.p50_ms}ms, "
                        f"p95 {measured_metrics.p95_ms}ms, p99 {measured_metrics.p99_ms}ms."
                    ),
                    evidence_source="k6.http_req_duration",
                ),
                Observation(
                    metric_or_signal="Reliability & Error Rate",
                    observed_fact=f"Measured error rate of {measured_metrics.error_rate * 100:.2f}% across {measured_metrics.vus} peak VUs.",
                    evidence_source="k6.http_req_failed",
                ),
            ]

            all_thresholds_passed = all(t.passed for t in threshold_evals)
            overall_status = "PASSED" if all_thresholds_passed else "DEGRADED"

            findings = [
                f"SLA Compliance outcome: {overall_status}.",
                f"Peak load sustained: {measured_metrics.vus} VUs with p95 at {measured_metrics.p95_ms}ms.",
            ]
            if measured_metrics.error_rate > 0.01:
                findings.append(f"Elevated error rate observed: {measured_metrics.error_rate * 100:.2f}%.")

            recommendations = []
            if overall_status == "PASSED":
                recommendations.append("System successfully met all SLA performance requirements under target load.")
            else:
                recommendations.append("Investigate endpoint latency under concurrency; consider connection pool tuning or caching.")

            analysis = AnalysisResult(
                analysis_id=f"analysis_{run_id[:8]}",
                test_id=test_spec.test_id,
                overall_status=overall_status,
                observations=obs,
                threshold_results=exec_res.thresholds,
                performance_findings=findings,
                possible_bottlenecks=[],
                recommendations=recommendations,
                confidence=0.95,
                sla_assessments=sla_assessments,
            )

            await self.db.save_artifact(run_id, "analysis_result", analysis.model_dump())
            await self.emit_event(
                run_id=run_id,
                state=RunState.ANALYSING_RESULTS,
                event_type="stage_completed",
                source="performance_analyst",
                message=f"Performance Analyst: SLA status '{analysis.overall_status}' (Confidence: {analysis.confidence * 100:.0f}%).",
                details={"overall_status": analysis.overall_status, "confidence": analysis.confidence},
            )

            # -----------------------------------------------------------------
            # State: DECIDING_NEXT_TEST (Adaptive Boundary Search)
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.DECIDING_NEXT_TEST)

            peak_vus = max((s.target_vus for s in test_spec.load), default=10)
            decision = MetricsEvaluator.evaluate_decision(
                metrics=measured_metrics,
                threshold_evals=threshold_evals,
                current_vus=measured_metrics.vus or peak_vus,
                target_vus=peak_vus,
            )

            decision_dict = decision.model_dump()
            await self.db.save_artifact(run_id, "decision_result", decision_dict)
            await self.emit_event(
                run_id=run_id,
                state=RunState.DECIDING_NEXT_TEST,
                event_type="decision_evaluated",
                message=f"Adaptive Boundary Decision: {decision.decision} - {decision.reason}",
                details=decision_dict,
            )

            # -----------------------------------------------------------------
            # State: SUMMARIZING & REPORTING
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.SUMMARIZING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.SUMMARIZING,
                event_type="summarizing_started",
                message="Summarizing: Assembling engineering executive report and findings.",
            )

            await self.db.update_run_state(run_id, RunState.REPORTING)
            await self.emit_event(
                run_id=run_id,
                state=RunState.REPORTING,
                event_type="report_ready",
                message="Reporting: Final performance testing report generated.",
                details={"overall_status": analysis.overall_status},
            )

            # -----------------------------------------------------------------
            # State: COMPLETED
            # -----------------------------------------------------------------
            await self.db.update_run_state(run_id, RunState.COMPLETED)
            await self.emit_event(
                run_id=run_id,
                state=RunState.COMPLETED,
                event_type="run_completed",
                message="Run completed successfully with all stages verified.",
            )

        except asyncio.CancelledError:
            await self.db.update_run_state(run_id, RunState.CANCELLED, "Run cancelled")
            await self.emit_event(
                run_id=run_id,
                state=RunState.CANCELLED,
                event_type="run_cancelled",
                message="Run execution was cancelled.",
            )
        except Exception as exc:
            error_text = str(exc)
            await self.db.update_run_state(run_id, RunState.FAILED, error_text)
            await self.emit_event(
                run_id=run_id,
                state=RunState.FAILED,
                event_type="run_failed",
                message=f"Run encountered unhandled failure: {error_text}",
                details={"error": error_text},
            )

    async def _call_validator(
        self,
        original_spec: TestSpecification,
        adapted_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calls /validator's /api/v1/validate endpoint or falls back to in-process pipeline."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.validator_url}/api/v1/validate",
                    json={"spec": adapted_dict, "auto_compile": True},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            # Fall back to in-process PipelineOrchestrator
            pass

        # In-process execution fallback
        policy = build_safety_policy(original_spec)
        orch = PipelineOrchestrator(policy=policy)
        result = orch.run(adapted_dict, auto_compile=True)
        return result.model_dump()

    async def _call_compiler(self, normalized_dict: Dict[str, Any]) -> str:
        """Calls /validator's /api/v1/compile or falls back to in-process compiler."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.validator_url}/api/v1/compile",
                    json=normalized_dict,
                )
                if resp.status_code == 200:
                    return resp.json().get("compiled_k6_script", "")
        except Exception:
            pass

        from app.compiler.k6_compiler import K6Compiler
        return K6Compiler.compile(normalized_dict)
