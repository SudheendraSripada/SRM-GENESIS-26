import pytest
from app.validators.schema_validator import SchemaValidator
from app.models.validation_result import ErrorCatalog


def test_missing_required_fields():
    # Missing target and load
    data = {"version": "1.0"}
    spec, errs, warns = SchemaValidator.validate(data)
    assert spec is None
    assert len(errs) >= 2
    paths = [e.path for e in errs]
    assert "target" in paths
    assert "load" in paths
    assert all(e.code == ErrorCatalog.SCHEMA_MISSING_FIELD for e in errs)


def test_invalid_type_rejection():
    data = {
        "version": "1.0",
        "target": {"base_url": "https://example.com"},
        "load": {
            "start_vus": "fifty",  # Invalid type
            "target_vus": 100,
            "duration_seconds": 60
        }
    }
    spec, errs, warns = SchemaValidator.validate(data)
    assert spec is None
    type_errs = [e for e in errs if e.code == ErrorCatalog.SCHEMA_INVALID_TYPE]
    assert len(type_errs) >= 1
    assert "load.start_vus" in [e.path for e in type_errs]
