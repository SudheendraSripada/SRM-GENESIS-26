import json
from pathlib import Path
import pytest
from app.engine.pipeline_orchestrator import PipelineOrchestrator
from app.repair.repair_engine import RepairEngine
from app.models.safety_policy import SafetyPolicy
from app.models.validation_result import PipelineStatus, ErrorCatalog

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_golden_valid_stress():
    with open(FIXTURES_DIR / "valid_stress.json") as f:
        data = json.load(f)

    orchestrator = PipelineOrchestrator()
    result = orchestrator.run(data)

    assert result.status == PipelineStatus.VALID
    assert result.validation_score >= 90
    assert result.compiled_k6_script is not None
    assert "import http from 'k6/http';" in result.compiled_k6_script
    assert len(result.errors) == 0


def test_invalid_malformed_syntax():
    with open(FIXTURES_DIR / "invalid_malformed.json") as f:
        raw_text = f.read()

    orchestrator = PipelineOrchestrator()
    result = orchestrator.run(raw_text)

    assert result.status == PipelineStatus.REJECTED
    assert result.stages["syntax"] == "FAIL"
    assert any(e.code == ErrorCatalog.SYNTAX_INVALID_JSON for e in result.errors)


def test_invalid_ssrf_rejected():
    with open(FIXTURES_DIR / "invalid_ssrf.json") as f:
        data = json.load(f)

    orchestrator = PipelineOrchestrator()
    result = orchestrator.run(data)

    assert result.status == PipelineStatus.REJECTED
    assert result.stages["safety"] == "FAIL"
    assert any(e.code == ErrorCatalog.SAFETY_SSRF_PROHIBITED_IP for e in result.errors)


def test_repair_engine_duration_mismatch():
    with open(FIXTURES_DIR / "invalid_duration_mismatch.json") as f:
        data = json.load(f)

    orchestrator = PipelineOrchestrator()
    initial_res = orchestrator.run(data)
    assert initial_res.status == PipelineStatus.REJECTED

    repaired, fixes = RepairEngine.attempt_repair(data, initial_res.errors, SafetyPolicy())
    assert len(fixes) >= 1

    revalidated = orchestrator.run(repaired)
    assert revalidated.status == PipelineStatus.VALID
    assert revalidated.compiled_k6_script is not None
