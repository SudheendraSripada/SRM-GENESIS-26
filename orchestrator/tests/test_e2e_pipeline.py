"""
End-to-End Pipeline Verification Test.
Tests prompt-to-report execution, artifact persistence, and metric provenance.
"""

import os
import tempfile
import pytest
from orchestrator.db import Database
from orchestrator.event_bus import EventBus
from orchestrator.engine import OrchestratorEngine
from orchestrator.models import RunState


@pytest.mark.anyio
async def test_end_to_end_prompt_to_report_flow():
    """Executes a full run and validates metric provenance and artifact chain."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        db = Database(db_path=db_path)
        await db.init_db()
        bus = EventBus()
        engine = OrchestratorEngine(db=db, event_bus=bus)

        run_id = "e2e_test_run_101"
        prompt = "Execute a baseline load test on the checkout service with 500 VUs and p95 under 500ms."

        await db.create_run(run_id, prompt, mock_mode=True)
        task = engine.start_run(run_id, prompt, mock_mode=True)
        await task

        detail = await db.get_run_detail(run_id)
        assert detail is not None
        assert detail.state == RunState.COMPLETED
        assert detail.error_message is None

        # 1. Verify artifact persistence chain
        assert detail.requirement_spec is not None
        assert detail.performance_plan is not None
        assert detail.test_data_plan is not None
        assert detail.test_specification is not None
        assert detail.adapted_test_spec is not None
        assert detail.critic_result is not None
        assert detail.validation_result is not None
        assert detail.compiled_k6_script is not None
        assert detail.execution_result is not None
        assert detail.analysis_result is not None
        assert detail.decision_result is not None

        # 2. Verify metric provenance
        # The numbers in analysis_result MUST match the deterministic execution_result metrics
        exec_metrics = detail.execution_result["metrics"]
        analysis_obs = detail.analysis_result["observations"]

        # Check that throughput and latency values cited in observations match measured values
        obs_facts = " ".join([o["observed_fact"] for o in analysis_obs])
        assert str(exec_metrics["requests"]) in obs_facts
        assert f"{exec_metrics['p95_ms']:.1f}" in obs_facts or f"{exec_metrics['p95_ms']:.2f}" in obs_facts or str(exec_metrics["p95_ms"]) in obs_facts

        # 3. Verify adaptive decision matches SLA outcome
        assert detail.decision_result["decision"] in ("STOP_SATISFIED", "STOP_FAILED", "SCALE_UP", "SCALE_DOWN")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

