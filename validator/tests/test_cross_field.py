import pytest
from app.models.test_spec import TestSpec
from app.validators.cross_field_validator import CrossFieldValidator
from app.models.validation_result import ErrorCatalog


def test_duration_sum_mismatch():
    spec = TestSpec(
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": 5, "target_vus": 20, "duration_seconds": 100},
        stages=[
            {"duration_seconds": 60, "target_vus": 10},
            {"duration_seconds": 60, "target_vus": 20}  # Sum = 120 != 100
        ]
    )
    errs, warns = CrossFieldValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CROSS_FIELD_DURATION_MISMATCH for e in errs)


def test_get_request_with_body():
    spec = TestSpec(
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": 1, "target_vus": 5, "duration_seconds": 30},
        payload={"type": "json", "body": {"search": "query"}}
    )
    errs, warns = CrossFieldValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CROSS_FIELD_GET_WITH_BODY for e in errs)


def test_malformed_variable_token():
    spec = TestSpec(
        target={"base_url": "https://example.com", "endpoint": "/api/users/{{id", "method": "GET"},
        load={"start_vus": 1, "target_vus": 5, "duration_seconds": 30}
    )
    errs, warns = CrossFieldValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CROSS_FIELD_MALFORMED_VARIABLE_TOKEN for e in errs)
