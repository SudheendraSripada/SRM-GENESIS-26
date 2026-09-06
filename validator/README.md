# AI JSON to k6 Validation & Compilation Pipeline

A high-performance, deterministic verification and compilation engine that progressively validates raw AI-generated JSON packets across 8 discrete gates and compiles them into executable, production-ready **k6** performance testing scripts.

---

## Architecture Overview

```
                      AI AGENTS / USER JSON
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               VALIDATION & COMPILATION PIPELINE              │
│                                                              │
│  [Stage 1] SyntaxValidator       O(N) single-pass parser     │
│  [Stage 2] SchemaValidator       Pydantic v2 core types      │
│  [Stage 3] ConstraintValidator   O(1) bounds & regexes       │
│  [Stage 4] SemanticValidator     Stress/Spike/Soak logic     │
│  [Stage 5] CrossFieldValidator   Duration conservation       │
│  [Stage 6] SafetyValidator       SSRF, CIDR, VU firewall     │
│  [Stage 7] K6CompatValidator     Executor & metrics AST      │
│  [Stage 8] SpecNormalizer        Canonical Spec IR           │
│  [Stage 9] K6Compiler            Deterministic ES6 JS        │
│  [Stage 10] RepairEngine         Bounded auto-correction     │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
                   Valid k6 JavaScript Script
```

### The 8 Progressive Verification Gates

1. **Stage 1 (Syntax)**: Single-pass $O(N)$ streaming parser with Markdown fence stripping, bracket stack tracking, and exact line:column error offset reporting.
2. **Stage 2 (Schema)**: Pydantic v2 core structural type checking producing standardized dot-path locations (`loc`).
3. **Stage 3 (Primitive Constraints)**: $O(1)$ HTTP verb membership, protocol verification, and non-negative VU limits.
4. **Stage 4 (Semantic Profiles)**: Enforces test-type invariants (monotonically non-decreasing stress load curves $V_{i+1} \ge V_i$, soak test minimum duration $\ge 300$s, spike peak surge ratios).
5. **Stage 5 (Cross-Field Invariants)**: Verifies the stage duration conservation law ($\sum d_i = D_{\text{total}}$), flags `GET`/`HEAD` requests with entity bodies, and detects unclosed Mustache variable tokens (`{{var`).
6. **Stage 6 (Safety & Policy Gate)**: Immutable security firewall enforcing max VU limits ($\le 1000$), max duration ($\le 1800$s), allowed target domains, and SSRF defense (blocking `169.254.169.254` and private CIDRs).
7. **Stage 7 (k6 Compatibility)**: Verifies mapping to supported k6 executors (`ramping-vus`, `constant-vus`) and standard threshold metrics.
8. **Stage 8 (Normalizer & Compiler)**: Desugars shorthand units (`"5m"` $\to 300$), injects required headers, and deterministically synthesizes clean ES6 k6 JavaScript.

---

## Performance Benchmarks

| Test Packet | Gate Verdict | Validation Score | Latency ($\mu s$) | Throughput (ops/sec) |
| :--- | :--- | :--- | :--- | :--- |
| **Malformed Syntax** | `REJECTED` | `0/100` | **16.8 $\mu s$** | **~59,300 ops/s** |
| **Duration Mismatch** | `REJECTED` | `58/100` | **58.5 $\mu s$** | **~17,000 ops/s** |
| **Stress Inversion** | `REJECTED` | `58/100` | **76.7 $\mu s$** | **~13,000 ops/s** |
| **SSRF Metadata Attack** | `REJECTED` | `18/100` | **83.4 $\mu s$** | **~12,000 ops/s** |
| **Golden Spec (Full)** | `VALID` | `100/100` | **134.3 $\mu s$** | **~7,400 ops/s** |

---

## Quick Start

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
PYTHONPATH=. pytest tests -v
```

### 3. Launch FastAPI Server & Web Dashboard
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **http://localhost:8000** in your browser to interact with the visual dashboard.

---

## API Endpoints

- `POST /api/v1/validate` — Run raw JSON through the 8-stage verification pipeline.
- `POST /api/v1/repair` — Propose algorithmic self-healing repairs for detected violations.
- `POST /api/v1/compile` — Compile Canonical Spec IR into executable ES6 k6 JavaScript.
- `GET /api/v1/presets` — Retrieve golden and adversarial test case presets.
- `GET /api/v1/policy` — Inspect the active platform safety policy boundaries.

---

## Project Structure

```
k6_pipeline/
├── app/
│   ├── main.py                     # FastAPI application entrypoint
│   ├── models/                     # Pydantic v2 schemas & error catalogs
│   ├── validators/                 # Stages 1 to 7 verification modules
│   ├── normalizer/                 # Canonical AST desugaring
│   ├── compiler/                   # Deterministic ES6 JS synthesizer
│   ├── repair/                     # Algorithmic auto-repair engine
│   ├── engine/                     # Pipeline orchestrator
│   └── web/                        # Interactive dashboard (HTML/CSS/JS)
├── config/
│   └── safety_policy.json          # Default policy boundaries
├── tests/                          # 26 unit and integration test cases
└── benchmark.py                    # Performance benchmark harness
```
