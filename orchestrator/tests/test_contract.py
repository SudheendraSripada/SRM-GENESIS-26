"""
Contract Tests: Adapters and Cross-Service Invariants.
Validates that output from /agents adapted via spec_adapter strictly conforms
to the schema and validation constraints of /validator.
"""

import pytest
from app.models.test_spec import TestSpec
from app.engine.pipeline_orchestrator import PipelineOrchestrator
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_TEST_SPECIFICATION,
    MOCK_TEST_DATA_PLAN,
)
from orchestrator.adapters.spec_adapter import adapt_specification, build_safety_policy


def test_contract_adapted_spec_matches_validator_schema():
    """Verifies that adapt_specification produces a dict that cleanly instantiates TestSpec."""
    result = adapt_specification(MOCK_TEST_SPECIFICATION, MOCK_TEST_DATA_PLAN)
    adapted_dict = result.to_dict()

    # Must validate cleanly against validator's Pydantic model
    spec_model = TestSpec.model_validate(adapted_dict)

    assert spec_model.target.base_url == "http://staging-ecom.local"
    assert spec_model.target.endpoint == "/api/checkout"
    assert spec_model.target.method == "POST"
    assert spec_model.load.target_vus == 500
    assert len(spec_model.stages) == 3
    assert any(t.metric == "http_req_duration" for t in spec_model.thresholds)


def test_contract_adapted_spec_passes_all_validator_stages():
    """Verifies that the adapted spec achieves 100/100 through all verification stages."""
    result = adapt_specification(MOCK_TEST_SPECIFICATION, MOCK_TEST_DATA_PLAN)
    adapted_dict = result.to_dict()

    policy = build_safety_policy(MOCK_TEST_SPECIFICATION)
    orchestrator = PipelineOrchestrator(policy=policy)
    val_res = orchestrator.run(adapted_dict, auto_compile=True)

    assert val_res.status.value == "VALID"
    assert val_res.validation_score == 100
    assert val_res.errors == []
    assert len(val_res.stages) >= 8
    assert all(status == "PASS" for status in val_res.stages.values())
    assert val_res.compiled_k6_script is not None
    assert "export const options" in val_res.compiled_k6_script
