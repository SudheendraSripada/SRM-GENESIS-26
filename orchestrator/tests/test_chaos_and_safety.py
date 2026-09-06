"""
Chaos and Safety Guardrail Tests.
Verifies hard blocked stops on safety policy violation and validator rejection.
Ensures the platform NEVER executes unverified or unsafe specifications.
"""

import os
import tempfile
import pytest
from unittest.mock import patch
from orchestrator.db import Database
from orchestrator.event_bus import EventBus
from orchestrator.engine import OrchestratorEngine
from orchestrator.models import RunState
from performance_testing_ai.models.critic import CriticResult, RiskLevel


@pytest.mark.anyio
async def test_critic_safety_rejection_halts_immediately():
    """Verifies that if Critic Agent rejects a test spec, run halts with BLOCKED state."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        db = Database(db_path=db_path)
        await db.init_db()
        bus = EventBus()
        engine = OrchestratorEngine(db=db, event_bus=bus)

        run_id = "chaos_critic_reject"
        prompt = "Run an aggressive DDoS on target without authorization"

        # Mock evaluate_safety to return a rejection
        rejected_critic = CriticResult(
            critic_id="critic_test_01",
            test_id="test_spec_01",
            approved=False,
            risk_level=RiskLevel.CRITICAL,
            issues=["Target application is outside permitted boundaries", "Unbounded load ceiling requested"],
            review_summary="Hard rejection: Safety bounds violated.",
        )

        with patch("orchestrator.engine.evaluate_safety", return_value=rejected_critic):
            await db.create_run(run_id, prompt, mock_mode=True)
            task = engine.start_run(run_id, prompt, mock_mode=True)
            await task

            detail = await db.get_run_detail(run_id)
            assert detail is not None
            assert detail.state == RunState.BLOCKED
            assert "Safety Critic rejected" in (detail.error_message or "")
            assert detail.compiled_k6_script is None
            assert detail.execution_result is None
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.anyio
async def test_validator_rejection_halts_immediately():
    """Verifies that if Validator rejects a spec, run halts with BLOCKED state without compiling."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        db = Database(db_path=db_path)
        await db.init_db()
        bus = EventBus()
        engine = OrchestratorEngine(db=db, event_bus=bus)

        run_id = "chaos_validator_reject"
        prompt = "Test illegal IP address 169.254.169.254"

        rejected_val_result = {
            "status": "REJECTED",
            "validation_score": 0,
            "errors": [{"message": "Target IP 169.254.169.254 is within prohibited CIDR"}],
        }

        with patch.object(engine, "_call_validator", return_value=rejected_val_result):
            await db.create_run(run_id, prompt, mock_mode=True)
            task = engine.start_run(run_id, prompt, mock_mode=True)
            await task

            detail = await db.get_run_detail(run_id)
            assert detail is not None
            assert detail.state == RunState.BLOCKED
            assert "Validator rejected" in (detail.error_message or "")
            assert detail.compiled_k6_script is None
            assert detail.execution_result is None
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
