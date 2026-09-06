import pytest
from app.models.test_spec import TestSpec
from app.validators.semantic_validator import SemanticValidator
from app.models.validation_result import ErrorCatalog


def test_stress_test_decreasing_stages():
    spec = TestSpec(
        test={"type": "stress"},
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": 100, "target_vus": 10, "duration_seconds": 180},
        stages=[
            {"duration_seconds": 60, "target_vus": 100},
            {"duration_seconds": 60, "target_vus": 50},
            {"duration_seconds": 60, "target_vus": 10}
        ]
    )
    errs, warns = SemanticValidator.validate(spec)
    assert any(e.code == ErrorCatalog.SEMANTIC_STRESS_NON_INCREASING for e in errs)


def test_soak_test_too_short():
    spec = TestSpec(
        test={"type": "soak"},
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": 10, "target_vus": 10, "duration_seconds": 60},
        stages=[
            {"duration_seconds": 60, "target_vus": 10}
        ]
    )
    errs, warns = SemanticValidator.validate(spec)
    assert any(e.code == ErrorCatalog.SEMANTIC_SOAK_TOO_SHORT for e in errs)
