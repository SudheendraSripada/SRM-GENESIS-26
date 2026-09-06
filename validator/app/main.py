import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models.safety_policy import SafetyPolicy
from app.models.validation_result import ValidationResult, ValidationErrorItem
from app.engine.pipeline_orchestrator import PipelineOrchestrator
from app.repair.repair_engine import RepairEngine
from app.compiler.k6_compiler import K6Compiler

app = FastAPI(
    title="k6 AI Validation & Compilation Pipeline API",
    version="1.0.0",
    description="Progressively proves that AI JSON test packets are structurally sound, semantically coherent, safe, and k6-compatible."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
FIXTURES_DIR = BASE_DIR.parent / "tests" / "fixtures"
CONFIG_FILE = BASE_DIR.parent / "config" / "safety_policy.json"

# Load default safety policy
policy = SafetyPolicy.load_from_file(CONFIG_FILE)
orchestrator = PipelineOrchestrator(policy=policy)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ValidateRequest(BaseModel):
    spec: Any
    auto_compile: bool = True


class RepairRequest(BaseModel):
    spec: Dict[str, Any]
    errors: Optional[List[ValidationErrorItem]] = None


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>k6 Validation Dashboard loading...</h2>")


@app.get("/api/v1/policy")
async def get_policy():
    return policy.model_dump()


@app.get("/api/v1/presets")
async def list_presets():
    presets = {}
    if FIXTURES_DIR.exists():
        for fpath in FIXTURES_DIR.glob("*.json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    try:
                        presets[fpath.stem] = json.loads(content)
                    except Exception:
                        presets[fpath.stem] = content
            except Exception:
                pass
    return presets


@app.post("/api/v1/validate", response_model=ValidationResult)
async def validate_spec(req: ValidateRequest):
    result = orchestrator.run(req.spec, auto_compile=req.auto_compile)
    return result


@app.post("/api/v1/repair")
async def repair_spec(req: RepairRequest):
    # If errors were not passed, run validation first to find them
    validation_run = orchestrator.run(req.spec, auto_compile=False)
    errors_to_fix = req.errors if req.errors is not None else validation_run.errors

    repaired_spec, applied_fixes = RepairEngine.attempt_repair(
        raw_dict=req.spec,
        errors=errors_to_fix,
        policy=policy
    )

    # Re-validate the repaired spec to confirm health
    revalidated_result = orchestrator.run(repaired_spec, auto_compile=True)

    return {
        "original_valid": validation_run.status,
        "applied_fixes": applied_fixes,
        "repaired_spec": repaired_spec,
        "revalidated_result": revalidated_result
    }


@app.post("/api/v1/compile")
async def compile_spec(req: Dict[str, Any]):
    try:
        script = K6Compiler.compile(req)
        return {"compiled_k6_script": script}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Compilation error: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
