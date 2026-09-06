import pytest
from app.models.test_spec import TestSpec
from app.normalizer.spec_normalizer import SpecNormalizer
from app.compiler.k6_compiler import K6Compiler


def test_normalization_and_compilation():
    spec = TestSpec(
        target={"base_url": "https://example.com/", "endpoint": "login", "method": "post"},
        load={"start_vus": 10, "target_vus": 50, "duration_seconds": 60},
        payload={"type": "json", "body": {"user": "alice"}}
    )

    norm = SpecNormalizer.normalize(spec)
    assert norm["target"]["base_url"] == "https://example.com"
    assert norm["target"]["endpoint"] == "/login"
    assert norm["target"]["method"] == "POST"
    assert "application/json" in norm["headers"]["Content-Type"]

    js_code = K6Compiler.compile(norm)
    assert "import http from 'k6/http';" in js_code
    assert "export const options =" in js_code
    assert "http.post(url, payload, params);" in js_code
    assert "check(response," in js_code
