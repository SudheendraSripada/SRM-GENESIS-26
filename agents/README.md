# Performance Testing AI (IEEE Genesis)

An AI-powered performance testing platform built with CrewAI, Python 3.13, and Pydantic.

---

## 1. Project Purpose

The purpose of **Performance Testing AI** is to automate the end-to-end performance engineering lifecycle—from translating vague user requirements into rigorous test specifications, to validating safety bounds, to interpreting metrics into actionable insights without human bias.

> **Core Safety Principle:**
>
> **Agents decide WHAT should be tested.**  
> **The execution layer will later decide HOW to safely execute it.**  
> **Agents never directly execute k6 or shell commands.**

---

## 2. Six Specialized Agents (Phase 2 Production Prompts)

The architecture enforces strict separation of responsibilities across 6 autonomous, sequential agents with domain-specific prompts in `src/performance_testing_ai/config/agents.yaml`:

| Agent | Responsibility | Key Engineering Prompt Focus |
|---|---|---|
| **1. Requirement Analyst** | Converts natural-language requirements into `RequirementSpec`. | Categorizes input into FACT, INFERENCE, MISSING, and AMBIGUITY. Inferred endpoints are explicitly flagged with `is_assumed=True`. Never hallucinates base URLs. Deduce test types (baseline, load, stress, soak). |
| **2. Performance Planner** | Converts `RequirementSpec` into `PerformancePlan`. | Translates concurrency targets into staged execution profiles (ramp-up, steady-state, ramp-down). Never uses abrupt single-step spikes. Preserves user thresholds and defines automated circuit breakers. |
| **3. Test Data Agent** | Formulates deterministic `TestDataPlan`. | Defines deterministic generation strategies (Faker seeds, indexed range pools, pre-seeded accounts) without generating millions of rows directly in the prompt. Handles static, dynamic, correlated, and unique data. |
| **4. Workload Builder** | Synthesizes contracts into declarative `TestSpecification`. | Strictly declarative specification of HTTP steps, payloads, and hard `SafetyConstraintsSpec` (`max_vus`, `max_duration_seconds`, `allowed_domains`, `max_rps`). Never generates arbitrary executable JavaScript or shell commands. |
| **5. Critic / Safety Agent** | Independent gatekeeper auditing `TestSpecification`. | Evaluates 10 safety and validity categories. Approves safe specifications or rejects unsafe/ambiguous ones with actionable issues and required remediations. |
| **6. Performance Analyst** | Analyzes `ExecutionResult` into `AnalysisResult`. | Strictly partitions empirical measurements (`Observation`) from unproven theories (`Hypothesis`). Requires concrete instrumentation evidence before confirming root causes. |

---

## 3. Data Flow & Sequential Pipeline

```text
User Natural Language Request
             │
             ▼
[1] Requirement Analyst Agent
             │  Output: RequirementSpec
             ▼
[2] Performance Planner Agent
             │  Output: PerformancePlan (context: Task 1)
             ▼
[3] Test Data Agent
             │  Output: TestDataPlan (context: Tasks 1 & 2)
             ▼
[4] Workload Builder Agent
             │  Output: TestSpecification (context: Tasks 1, 2, & 3)
             ▼
[5] Critic / Safety Agent
             │  Output: CriticResult (context: Task 4)
             ▼
   APPROVED TEST SPECIFICATION
             │
             ▼
 [Future: K6 Execution Engine]
             │  Output: ExecutionResult
             ▼
[6] Performance Analyst Agent
             │  Output: AnalysisResult (context: Task 4 + ExecutionResult)
             ▼
Final Diagnostic Report & Recommendations
```

---

## 4. Pydantic Data Contracts

All models reside under `src/performance_testing_ai/models/`:

1. **`RequirementSpec`**: `user_request`, `target_application`, `target_base_url`, `endpoints`, `expected_users`, `duration`, `test_type`, `performance_goals`, `thresholds`, `assumptions`, `missing_information`.
2. **`PerformancePlan`**: `plan_id`, `test_type`, `objective`, `stages`, `ramp_up`, `steady_state`, `ramp_down`, `target_vus`, `duration`, `thresholds`, `success_criteria`, `assumptions`.
3. **`TestDataPlan`**: `data_plan_id`, `plan_id`, `users_required`, `unique_users_required`, `payload_requirements`, `product_data_requirements`, `authentication_requirements`, `correlation_requirements`, `data_generation_strategy`, `assumptions`.
4. **`TestSpecification`**: `test_id`, `test_name`, `objective`, `test_type`, `target`, `load`, `thresholds`, `data_requirements`, `authentication_requirements`, `request_sequence`, `success_criteria`, `assumptions`, `safety_constraints`.
5. **`CriticResult`**: `critic_id`, `test_id`, `approved`, `risk_level`, `issues`, `warnings`, `required_changes`, `safety_checks`, `review_summary`.
6. **`ExecutionResult`**: `test_id`, `status`, `start_time`, `end_time`, `metrics` (`requests`, `rps`, `avg_latency_ms`, `p95_ms`, `p99_ms`, `error_rate`, `iterations`), `thresholds`, `errors`, `raw_summary_reference`.
7. **`AnalysisResult`**: `analysis_id`, `test_id`, `overall_status`, `observations`, `threshold_results`, `performance_findings`, `possible_bottlenecks`, `degradation_point`, `recommendations`, `confidence`, `limitations`, `hypotheses`.

---

## 5. LLM Provider Configuration (Phase 2)

The project includes an extensible LLM provider abstraction in `src/performance_testing_ai/llm_config.py` supporting:
- **Mock Mode (Default)**: Zero-cost, deterministic local execution with no API keys or internet required (`PERFORMANCE_TESTING_MOCK_MODE=true`).
- **Google Gemini**: Via `GEMINI_API_KEY` and `GEMINI_MODEL_NAME=gemini/gemini-3.5-flash`.
- **OpenAI**: Via `OPENAI_API_KEY` and `OPENAI_MODEL_NAME=gpt-4o-mini`.
- **Ollama / Local LLM**: Via `OLLAMA_BASE_URL=http://localhost:11434` and `OLLAMA_MODEL=ollama/llama3.2`.
- **Anthropic**: Via `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL=anthropic/claude-3-5-sonnet-20241022`.

Configure via `.env` (refer to [.env.example](file:///c:/Users/NAGA%20TRIBHARGAV/performance-testing-ai/.env.example)).

---

## 6. How to Run

### Run CLI in MOCK_MODE:
```powershell
uv run performance-testing-ai
```
Or with a custom query:
```powershell
uv run performance-testing-ai --request "Test whether my e-commerce application can handle 500 concurrent users during checkout. p95 should stay below 500 ms and errors below 1%."
```

### Run Automated Tests:
```powershell
uv run pytest -v
```

---

## 7. Safety Boundaries

- **No Tool Execution**: All 6 agents are instantiated with `tools=[]` and `allow_delegation=False`.
- **No Shell/Code Execution**: Agents cannot execute shell commands, Python scripts, JavaScript, or Docker commands.
- **Declarative Only**: The Workload Builder outputs a declarative specification; it never compiles or executes k6 code.
- **Critic Rejection**: The Critic Agent deterministically validates target domains, load limits, and step sequences, rejecting any test that violates safety limits.
- **Empirical Rigor**: The Performance Analyst strictly partitions measured facts (`Observation`) from unverified root-cause theories (`Hypothesis`), requiring concrete instrumentation evidence before confirming causes.

---

## 8. Phase 3A: Deterministic TestSpecification Validator

The platform features a completely deterministic validation boundary (`src/performance_testing_ai/execution/validator.py`) executing prior to any future k6 script compilation:

```text
TestSpecification
       │
       ▼
Deterministic Validator  (validate_test_specification)
       │
       ▼
ValidationResult (valid: true/false, structured errors, warnings)
       │
       ▼
[Future Phase 3B: k6 Compiler]
```

### Validator Guarantees:
- **Zero External Side Effects**: Pure Python validation without network traffic, shell calls, Docker, or LLM invocations.
- **Strict Hostname Whitelisting**: Matches exact hostnames or legitimate subdomains; strictly prevents domain spoofing (e.g. `example.com.evil.com` or `evil-example.com` are rejected).
- **Safety Enforcement**: Enforces `max_vus` concurrency limits, total test duration ceiling, non-empty request sequences, and respects upstream Critic gate approval (`CRITIC_GATE_REJECTED`).
- **Read-Only & Deterministic**: Input specifications are never mutated; identical inputs produce identical `ValidationResult` objects.

---

## 9. Phase 3B: Deterministic k6 Script Compiler

The platform contains a deterministic compiler (`src/performance_testing_ai/execution/compiler.py`) translating a validated `TestSpecification` into standalone k6 JavaScript:

```text
TestSpecification
       │
       ▼
Phase 3A Deterministic Validator
       │
       ▼
ValidationResult.valid == True
       │
       ▼
Phase 3B Deterministic k6 Compiler  (compile_k6_script)
       │
       ▼
k6 JavaScript String
       │
       ▼
[Future Phase 3C: JavaScript Validator]
       │
       ▼
[Future Phase 3D: Safe k6 Runner]
```

### Compiler Guarantees:
- **Pure Translation Function**: Zero side effects, zero network calls, zero shell/k6 execution, no file writes.
- **100% Deterministic**: Identical specifications produce byte-for-byte identical k6 JavaScript code.
- **Strict Immutability**: The input `TestSpecification` is never modified.
- **Secure Escaping**: All strings (endpoints, headers, parameters) are safely JSON-escaped; eliminates template and script injection vulnerabilities.
- **No Silent Auto-Fixes**: Rejects invalid or out-of-bounds specifications with deterministic `CompilationError` exceptions.

---

## 10. Current Implementation Status (Phase 3B Completed)

- [x] Python 3.13 + UV virtual environment configuration.
- [x] 7 strongly-typed Pydantic data contracts with field validations.
- [x] 6 specialized CrewAI agents configured with production prompts in `agents.yaml`.
- [x] 6 sequential CrewAI tasks configured with detailed context chaining and Pydantic output mappings in `tasks.yaml`.
- [x] Configurable LLM provider abstraction (`llm_config.py`) supporting Mock, Gemini, OpenAI, Ollama, and Anthropic.
- [x] Deterministic safety evaluation engine in `critic_agent.py`.
- [x] `MOCK_MODE` pipeline orchestrator (`pipeline.py`) and CLI entry point (`main.py`).
- [x] Phase 3A Deterministic TestSpecification Validator (`validator.py`) and `ValidationResult` contract.
- [x] **Phase 3B Deterministic k6 Script Compiler** (`compiler.py`).
- [x] **74 automated unit, validation, compiler, contract, and pipeline tests (100% pass rate).**
- [x] Complete environment template in `.env.example`.

---

## 11. What is Intentionally NOT Implemented Yet

In adherence to strict scope boundaries:
- [ ] Phase 3C: No generated JavaScript AST or syntax validator yet.
- [ ] Phase 3D: No k6 installation, local subprocess execution, or script execution yet.
- [ ] Phase 3E: No k6 summary output parser yet.
- [ ] Phase 3F: No pipeline/orchestration integration bridging Task 5 and Task 6 yet.
- [ ] No Docker container creation or management.
- [ ] No FastAPI execution service.
- [ ] No Supabase or external database integration.


"# SRM_HACK" 
