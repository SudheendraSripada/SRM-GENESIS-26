import pytest
from app.models.test_spec import TestSpec
from app.models.safety_policy import SafetyPolicy
from app.validators.safety_validator import SafetyValidator
from app.models.validation_result import ErrorCatalog


def test_safety_vus_exceeded():
    policy = SafetyPolicy(max_vus=500)
    spec = TestSpec(
        target={"base_url": "https://example.com", "method": "GET"},
        load={"start_vus": 10, "target_vus": 600, "duration_seconds": 60}
    )
    errs, warns = SafetyValidator.validate(spec, policy)
    assert any(e.code == ErrorCatalog.SAFETY_MAX_VUS_EXCEEDED for e in errs)


def test_safety_ssrf_prohibited_ip():
    policy = SafetyPolicy()
    spec = TestSpec(
        target={"base_url": "http://169.254.169.254", "endpoint": "/latest", "method": "GET"},
        load={"start_vus": 1, "target_vus": 5, "duration_seconds": 30}
    )
    errs, warns = SafetyValidator.validate(spec, policy)
    assert any(e.code == ErrorCatalog.SAFETY_SSRF_PROHIBITED_IP for e in errs)


def test_safety_target_not_allowed():
    policy = SafetyPolicy(allowed_targets=["https://internal.test.net"])
    spec = TestSpec(
        target={"base_url": "https://malicious-external-target.com", "method": "GET"},
        load={"start_vus": 1, "target_vus": 5, "duration_seconds": 30}
    )
    errs, warns = SafetyValidator.validate(spec, policy)
    assert any(e.code == ErrorCatalog.SAFETY_TARGET_NOT_ALLOWED for e in errs)
