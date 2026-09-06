import pytest
from app.models.test_spec import TestSpec
from app.validators.constraint_validator import ConstraintValidator
from app.models.validation_result import ErrorCatalog


def test_invalid_http_method():
    spec = TestSpec(
        target={"base_url": "https://example.com", "method": "INVALID_METHOD"},
        load={"start_vus": 10, "target_vus": 50, "duration_seconds": 60}
    )
    errs, warns = ConstraintValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CONSTRAINT_INVALID_METHOD for e in errs)


def test_negative_vus():
    spec = TestSpec(
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": -5, "target_vus": 0, "duration_seconds": 60}
    )
    errs, warns = ConstraintValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CONSTRAINT_VUS_RANGE for e in errs)


def test_invalid_url_scheme():
    spec = TestSpec(
        target={"base_url": "ftp://example.com", "method": "GET"},
        load={"start_vus": 1, "target_vus": 10, "duration_seconds": 60}
    )
    errs, warns = ConstraintValidator.validate(spec)
    assert any(e.code == ErrorCatalog.CONSTRAINT_INVALID_URL for e in errs)
