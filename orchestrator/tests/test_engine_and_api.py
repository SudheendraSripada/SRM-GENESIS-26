"""
Tests for Orchestrator State Machine Engine, SQLite Persistence, and FastAPI Endpoints.
"""

import asyncio
import os
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport

from orchestrator.models import CreateRunRequest, RunState
from orchestrator.db import Database
from orchestrator.event_bus import EventBus
from orchestrator.engine import OrchestratorEngine
from orchestrator.main import app, db as global_db, engine as global_engine


@pytest.fixture
async def test_env():
    """Creates an isolated temporary SQLite database and orchestrator engine."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    db = Database(db_path=temp_db_path)
    await db.init_db()
    bus = EventBus()
    eng = OrchestratorEngine(db=db, event_bus=bus)

    yield {"db": db, "bus": bus, "engine": eng, "db_path": temp_db_path}

    try:
        os.remove(temp_db_path)
    except OSError:
        pass


@pytest.mark.anyio
async def test_full_run_lifecycle_completes(test_env):
    """Verifies that a valid run transitions from CREATED all the way to COMPLETED."""
    db: Database = test_env["db"]
    eng: OrchestratorEngine = test_env["engine"]

    run_id = "test_run_1"
    prompt = "Test whether checkout can handle 500 concurrent users with p95 < 500ms."

    await db.create_run(run_id, prompt, mock_mode=True)
    task = eng.start_run(run_id, prompt, mock_mode=True)
    await task

    detail = await db.get_run_detail(run_id)
    assert detail is not None
    assert detail.state == RunState.COMPLETED
    assert detail.completed_at is not None

    # Check all required artifacts are stored
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

    # Check events sequence
    events = detail.events
    assert len(events) >= 10
    event_states = [e.state for e in events]
    assert RunState.CREATED in event_states
    assert RunState.ANALYSING in event_states
    assert RunState.PLANNING in event_states
    assert RunState.CRITIC_REVIEW in event_states
    assert RunState.VALIDATING in event_states
    assert RunState.BUILDING in event_states
    assert RunState.EXECUTING in event_states
    assert RunState.ANALYSING_RESULTS in event_states
    assert RunState.COMPLETED in event_states


@pytest.mark.anyio
async def test_validator_rejection_causes_hard_blocked_stop(test_env):
    """
    Asserts that if validator rejects the specification, the orchestrator
    transitions to BLOCKED and NEVER silently retries or fakes success.
    """
    db: Database = test_env["db"]
    bus: EventBus = test_env["bus"]

    # Engine with mocked invalid validator that rejects the spec
    eng = OrchestratorEngine(db=db, event_bus=bus, validator_url="http://invalid-fake-host")

    # Monkeypatch _call_validator to return a REJECTED result
    async def fake_rejected_validator(original_spec, adapted_dict):
        return {
            "status": "REJECTED",
            "validation_score": 15,
            "errors": [
                {
                    "code": "SAFETY_001",
                    "stage": "safety",
                    "path": "load.target_vus",
                    "message": "Requested target_vus (5000) exceeds maximum platform policy (1000)",
                    "severity": "CRITICAL",
                }
            ],
            "warnings": [],
        }

    eng._call_validator = fake_rejected_validator

    run_id = "test_run_blocked"
    prompt = "DDoS attack target with 100000 VUs"
    await db.create_run(run_id, prompt, mock_mode=True)

    task = eng.start_run(run_id, prompt, mock_mode=True)
    await task

    detail = await db.get_run_detail(run_id)
    assert detail is not None
    assert detail.state == RunState.BLOCKED
    assert "exceeds maximum platform policy" in (detail.error_message or "")

    # Assert execution was NOT run
    assert detail.execution_result is None
    assert detail.analysis_result is None

    # Verify blocked event
    blocked_events = [e for e in detail.events if e.state == RunState.BLOCKED]
    assert len(blocked_events) == 1
    assert blocked_events[0].event_type == "validation_blocked"


@pytest.mark.anyio
async def test_cancellation_flow(test_env):
    """Verifies that an active run can be cancelled and transitions to CANCELLED."""
    db: Database = test_env["db"]
    bus: EventBus = test_env["bus"]

    class PausingEngine(OrchestratorEngine):
        async def _execute_run(self, run_id: str, prompt: str, mock_mode: bool = True):
            await self.emit_event(run_id, RunState.ANALYSING, "started", "Paused for test")
            await asyncio.sleep(10.0)

    eng = PausingEngine(db=db, event_bus=bus)
    run_id = "test_run_cancel"
    await db.create_run(run_id, "Some test prompt", mock_mode=True)

    eng.start_run(run_id, "Some test prompt", mock_mode=True)
    await asyncio.sleep(0.05)

    cancelled = await eng.cancel_run(run_id)
    assert cancelled is True

    detail = await db.get_run_detail(run_id)
    assert detail is not None
    assert detail.state == RunState.CANCELLED


@pytest.mark.anyio
async def test_fastapi_endpoints():
    """Tests the FastAPI REST endpoints using httpx AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # 2. Create Run
        create_resp = await client.post(
            "/api/v1/runs",
            json={"prompt": "Test my login API with 50 VUs and p95 < 200ms", "mock_mode": True},
        )
        assert create_resp.status_code == 201
        run_data = create_resp.json()
        run_id = run_data["run_id"]
        assert run_id.startswith("run_")
        assert run_data["state"] == "CREATED"

        # Wait briefly for execution task to progress
        await asyncio.sleep(0.5)

        # 3. List runs
        list_resp = await client.get("/api/v1/runs")
        assert list_resp.status_code == 200
        runs = list_resp.json()
        assert any(r["run_id"] == run_id for r in runs)

        # 4. Get run detail
        detail_resp = await client.get(f"/api/v1/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["run_id"] == run_id
        assert "events" in detail
        assert len(detail["events"]) > 0
