"""
Unit and integration tests for orchestrator/adapters/spec_adapter.py.
Validates contract transformation from CrewAI agents to FastAPI validator schema
and verifies compliance with all 8 validation stages of PipelineOrchestrator.
"""

import json
import pytest

from performance_testing_ai.models.requirement import HttpMethod, TestType, ThresholdSpec
from performance_testing_ai.models.performance_plan import StageSpec
from performance_testing_ai.models.test_specification import (
    TestSpecification,
    TargetSystemSpec,
    HttpStepSpec,
    SafetyConstraintsSpec,
)
from performance_testing_ai.models.test_data import (
    TestDataPlan,
    ParameterizationRule,
    DatasetRequirement,
    UserProfileSpec,
    DataStrategy,
    SelectionMode,
)
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_TEST_SPECIFICATION,
    MOCK_TEST_DATA_PLAN,
)

from app.engine.pipeline_orchestrator import PipelineOrchestrator
from app.models.validation_result import PipelineStatus, StageStatus
from app.models.safety_policy import SafetyPolicy

from orchestrator.adapters.spec_adapter import (
    adapt_specification,
    build_safety_policy,
    parse_duration_seconds,
    resolve_payload_body,
    AgentEvent,
    AdaptationResult,
)


class TestSpecAdapterDurations:
    """Tests duration string parsing into total seconds."""

    def test_parse_duration_seconds_standard(self):
        assert parse_duration_seconds("30s") == 30
        assert parse_duration_seconds("2m") == 120
        assert parse_duration_seconds("1h") == 3600
        assert parse_duration_seconds("2m30s") == 150
        assert parse_duration_seconds(45) == 45
        assert parse_duration_seconds(45.0) == 45

    def test_parse_duration_seconds_fallback(self):
        assert parse_duration_seconds("") == 60
        assert parse_duration_seconds("invalid") == 60
        assert parse_duration_seconds(None) == 60


class TestSpecAdapterPayloadResolution:
    """Tests resolution of declarative payload schemas into real data."""

    def test_resolve_payload_with_test_data_plan(self):
        step = HttpStepSpec(
            name="Checkout Step",
            endpoint="/api/checkout",
            method=HttpMethod.POST,
            payload_schema={
                "cart_id": "string",
                "payment_token": "string",
                "quantity": "int",
                "price": "float",
                "is_gift": "bool",
                "literal_val": "concrete_123",
            },
        )
        data_plan = TestDataPlan(
            data_plan_id="dp-1",
            plan_id="p-1",
            users_required=10,
            unique_users_required=True,
            payload_requirements=[],
            product_data_requirements=[],
            authentication_requirements=[],
            correlation_requirements=[],
            data_generation_strategy="test",
            assumptions=[],
            parameterization_rules=[
                ParameterizationRule(
                    parameter_name="cart_id",
                    source_dataset="carts",
                    selection_mode=SelectionMode.UNIQUE,
                )
            ],
        )

        resolved = resolve_payload_body(step, data_plan)
        assert isinstance(resolved, dict)
        assert resolved["cart_id"] == "cart_id_test_1001"
        assert resolved["payment_token"] == "tok_test_payment_token"
        assert resolved["quantity"] == 1
        assert resolved["price"] == 19.99
        assert resolved["is_gift"] is True
        assert resolved["literal_val"] == "concrete_123"

    def test_resolve_payload_nested(self):
        step_dict = {
            "name": "Order Step",
            "endpoint": "/api/orders",
            "method": "POST",
            "payload_schema": {
                "order": {
                    "item_id": "int",
                    "customer_email": "string",
                },
                "items": ["string"],
            },
        }
        resolved = resolve_payload_body(step_dict, None)
        assert resolved["order"]["item_id"] == 1001
        assert resolved["order"]["customer_email"] == "test_user@example.com"
        assert resolved["items"] == ["sku_test_1001"]


class TestSpecAdapterMultiStepSimplification:
    """Tests MVP multi-step simplification and AgentEvent emission."""

    def test_multi_step_request_emits_event(self):
        spec = TestSpecification(
            test_id="spec-multi",
            test_name="Multi-step Scenario",
            objective="Test checkout pipeline",
            test_type=TestType.LOAD,
            target=TargetSystemSpec(base_url="https://example.com"),
            load=[StageSpec(duration="1m", target_vus=10)],
            request_sequence=[
                HttpStepSpec(name="Step 1 Login", endpoint="/api/login", method=HttpMethod.POST),
                HttpStepSpec(name="Step 2 Browse", endpoint="/api/browse", method=HttpMethod.GET),
                HttpStepSpec(name="Step 3 Checkout", endpoint="/api/checkout", method=HttpMethod.POST),
            ],
            safety_constraints=SafetyConstraintsSpec(max_vus=20, max_duration_seconds=120),
        )

        res = adapt_specification(spec)

        # Primary step must be request_sequence[0]
        assert res.spec.target.endpoint == "/api/login"
        assert res.spec.target.method == "POST"

        # AgentEvent must be emitted
        assert len(res.events) == 1
        event = res.events[0]
        assert event.event_type == "scenario_simplified"
        assert "simplified to primary endpoint '/api/login'" in event.message
        assert event.details["total_steps"] == 3
        assert len(event.details["omitted_steps"]) == 2
        assert event.details["omitted_steps"][0]["endpoint"] == "/api/browse"

    def test_single_step_request_no_simplification_event(self):
        spec = TestSpecification(
            test_id="spec-single",
            test_name="Single Step",
            objective="Test endpoint",
            test_type=TestType.LOAD,
            target=TargetSystemSpec(base_url="https://example.com"),
            load=[StageSpec(duration="1m", target_vus=10)],
            request_sequence=[
                HttpStepSpec(name="Step 1", endpoint="/api/search", method=HttpMethod.GET),
            ],
            safety_constraints=SafetyConstraintsSpec(max_vus=20, max_duration_seconds=120),
        )

        res = adapt_specification(spec)
        assert res.spec.target.endpoint == "/api/search"
        assert res.spec.target.method == "GET"
        assert len(res.events) == 0


class TestSpecAdapterHttpInvariants:
    """Tests that HTTP method and body constraints are preserved."""

    def test_get_request_omits_payload_body_and_emits_event(self):
        spec = TestSpecification(
            test_id="spec-get-body",
            test_name="GET with Schema",
            objective="Test search",
            test_type=TestType.LOAD,
            target=TargetSystemSpec(base_url="https://example.com"),
            load=[StageSpec(duration="1m", target_vus=10)],
            request_sequence=[
                HttpStepSpec(
                    name="Search",
                    endpoint="/api/search",
                    method=HttpMethod.GET,
                    payload_schema={"query": "string"},
                ),
            ],
            safety_constraints=SafetyConstraintsSpec(max_vus=20, max_duration_seconds=120),
        )

        res = adapt_specification(spec)
        # Body must be None for GET requests
        assert res.spec.payload.body is None
        assert res.spec.payload.type == "none"

        # Event must explain omission
        omission_events = [e for e in res.events if e.event_type == "payload_omitted_for_get"]
        assert len(omission_events) == 1

    def test_post_request_injects_content_type(self):
        spec = TestSpecification(
            test_id="spec-post-json",
            test_name="POST JSON",
            objective="Test creation",
            test_type=TestType.LOAD,
            target=TargetSystemSpec(base_url="https://example.com", default_headers={}),
            load=[StageSpec(duration="1m", target_vus=10)],
            request_sequence=[
                HttpStepSpec(
                    name="Create",
                    endpoint="/api/items",
                    method=HttpMethod.POST,
                    payload_schema={"title": "string"},
                ),
            ],
            safety_constraints=SafetyConstraintsSpec(max_vus=20, max_duration_seconds=120),
        )

        res = adapt_specification(spec)
        assert res.spec.payload.type == "json"
        assert res.spec.payload.body == {"title": "Test Title"}
        assert res.spec.headers.get("Content-Type") == "application/json"


class TestSpecAdapterFullPipelineIntegration:
    """
    Tests end-to-end integration by feeding adapted specifications
    into PipelineOrchestrator to verify all 8 validation stages pass.
    """

    def test_mock_fixture_passes_all_pipeline_stages(self):
        # 1. Adapt specification using MOCK fixtures
        result = adapt_specification(MOCK_TEST_SPECIFICATION, MOCK_TEST_DATA_PLAN)
        assert isinstance(result, AdaptationResult)

        # 2. Build conforming SafetyPolicy
        policy = build_safety_policy(MOCK_TEST_SPECIFICATION)
        orchestrator = PipelineOrchestrator(policy=policy)

        # 3. Run validation pipeline
        val_result = orchestrator.run(result.to_dict())

        # 4. Verify pipeline results
        assert val_result.status == PipelineStatus.VALID
        assert val_result.validation_score == 100
        assert val_result.errors == []
        assert val_result.warnings == []

        # 5. Check all individual stages
        for stage_name, status in val_result.stages.items():
            assert status == StageStatus.PASS, f"Stage {stage_name} did not pass: {status}"

        # 6. Verify k6 script compiled
        assert val_result.compiled_k6_script is not None
        assert "export default function ()" in val_result.compiled_k6_script
        assert "http://staging-ecom.local/api/checkout" in val_result.compiled_k6_script
        assert "cart_id_test_1001" in val_result.compiled_k6_script
        assert "tok_test_payment_token" in val_result.compiled_k6_script

    def test_dict_input_adaptation(self):
        spec_dict = MOCK_TEST_SPECIFICATION.model_dump()
        data_dict = MOCK_TEST_DATA_PLAN.model_dump()

        result = adapt_specification(spec_dict, data_dict)
        assert result.spec.metadata.test_id == "spec-ecom-500vu"
        assert result.spec.load.duration_seconds == 480
        assert result.spec.load.target_vus == 500

    def test_baseline_test_adaptation_and_validation(self):
        spec = TestSpecification(
            test_id="spec-baseline",
            test_name="Baseline Evaluation",
            objective="Baseline SLA check",
            test_type=TestType.BASELINE,
            target=TargetSystemSpec(base_url="https://example.com"),
            load=[
                StageSpec(duration="1m", target_vus=10),
                StageSpec(duration="2m", target_vus=10),
            ],
            thresholds=[
                ThresholdSpec(metric="http_req_duration", aggregation="p90", operator="<", value=200.0),
            ],
            request_sequence=[
                HttpStepSpec(name="Health", endpoint="/health", method=HttpMethod.GET, expected_status_codes=[200]),
            ],
            safety_constraints=SafetyConstraintsSpec(max_vus=50, max_duration_seconds=300),
        )

        result = adapt_specification(spec)
        policy = build_safety_policy(spec)
        orchestrator = PipelineOrchestrator(policy=policy)
        val_result = orchestrator.run(result.to_dict())

        assert val_result.status == PipelineStatus.VALID
        assert val_result.stages["semantic"] == StageStatus.PASS
        assert val_result.stages["k6_compatibility"] == StageStatus.PASS
        assert val_result.stages["compilation"] == StageStatus.PASS
