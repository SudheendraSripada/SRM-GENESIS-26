import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_presets():
    res = client.get("/api/v1/presets")
    assert res.status_code == 200
    data = res.json()
    assert "valid_stress" in data
    assert "invalid_malformed" in data


def test_api_validate_valid():
    payload = {
        "spec": {
            "version": "1.0",
            "target": {"base_url": "https://example.com", "method": "GET"},
            "load": {"start_vus": 1, "target_vus": 10, "duration_seconds": 30}
        },
        "auto_compile": True
    }
    res = client.post("/api/v1/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["compiled_k6_script"] is not None
    assert "http.get(url, params);" in data["compiled_k6_script"]


def test_api_validate_invalid():
    payload = {
        "spec": "{ invalid json",
        "auto_compile": True
    }
    res = client.post("/api/v1/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["stages"]["syntax"] == "FAIL"


def test_api_repair():
    bad_spec = {
        "version": "1.0",
        "target": {"base_url": "https://example.com", "method": "get"},
        "load": {"start_vus": 5, "target_vus": 10, "duration_seconds": 50},
        "stages": [
            {"duration_seconds": 30, "target_vus": 5},
            {"duration_seconds": 30, "target_vus": 10}
        ]
    }
    res = client.post("/api/v1/repair", json={"spec": bad_spec})
    assert res.status_code == 200
    data = res.json()
    assert len(data["applied_fixes"]) >= 1
    assert data["revalidated_result"]["status"] == "VALID"
