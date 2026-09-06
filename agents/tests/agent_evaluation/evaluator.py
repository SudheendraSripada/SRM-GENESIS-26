import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from performance_testing_ai.pipeline import PipelineContext
from tests.agent_evaluation.invariants import (
    ALL_INVARIANTS,
    BaseInvariant,
    InvariantResult,
    InvariantStatus,
)
from tests.agent_evaluation.scoring import (
    CaseScore,
    CaseVerdict,
    DIMENSION_NAMES,
    EvaluationSuiteReport,
    calculate_case_score,
)

class EvaluationCase(BaseModel):
    id: str
    category: str
    description: str
    user_request: str
    expected: Dict[str, Any] = Field(default_factory=dict)
    must_preserve: List[str] = Field(default_factory=list)
    must_not_invent: List[str] = Field(default_factory=list)
    expected_flags: List[str] = Field(default_factory=list)
    severity: str = "medium"

def load_test_cases(file_path: Optional[str] = None) -> List[EvaluationCase]:
    """Loads evaluation test cases from JSON file."""
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "test_cases.json")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [EvaluationCase(**c) for c in data]

class AgentEvaluator:
    """
    Core Evaluation Engine for testing AI agents against deterministic invariants,
    anti-hallucination rules, safety constraints, and cross-agent consistency.
    """

    def __init__(self, invariants: Optional[List[BaseInvariant]] = None):
        self.invariants = invariants if invariants is not None else ALL_INVARIANTS

    def evaluate_case(
        self,
        case: EvaluationCase | Dict[str, Any],
        context: PipelineContext,
    ) -> CaseScore:
        """Evaluates a single PipelineContext against all configured invariants."""
        case_dict = case.model_dump() if isinstance(case, EvaluationCase) else case
        case_id = case_dict.get("id", "UNKNOWN")

        results: List[InvariantResult] = []
        for inv in self.invariants:
            try:
                res = inv.evaluate(case_dict, context)
                results.append(res)
            except Exception as e:
                results.append(InvariantResult(
                    invariant_name=inv.name,
                    status=InvariantStatus.FAIL,
                    dimension=inv.dimension,
                    details=f"Exception during invariant evaluation: {e}",
                    failure_reason=str(e),
                ))

        return calculate_case_score(case_id, results)

    def evaluate_suite(
        self,
        cases: List[EvaluationCase],
        contexts: List[PipelineContext],
    ) -> EvaluationSuiteReport:
        """Evaluates an entire suite of test cases and generates an aggregate report."""
        if len(cases) != len(contexts):
            raise ValueError(f"Cases count ({len(cases)}) must match contexts count ({len(contexts)})")

        case_scores: List[CaseScore] = []
        passed = 0
        partial = 0
        failed = 0
        critical_failures = 0

        top_critical: List[str] = []
        top_hallucinations: List[str] = []
        top_thresholds: List[str] = []
        top_safety: List[str] = []
        metamorphic_results: List[str] = []

        dim_accumulators: Dict[str, List[float]] = {d: [] for d in DIMENSION_NAMES}

        # Cache by ID for metamorphic comparison
        scores_by_id: Dict[str, CaseScore] = {}
        cases_by_id: Dict[str, EvaluationCase] = {}

        for case, ctx in zip(cases, contexts):
            score = self.evaluate_case(case, ctx)
            case_scores.append(score)
            scores_by_id[case.id] = score
            cases_by_id[case.id] = case

            if score.verdict == CaseVerdict.PASS:
                passed += 1
            elif score.verdict == CaseVerdict.PARTIAL:
                partial += 1
            elif score.verdict == CaseVerdict.FAIL:
                failed += 1
            elif score.verdict == CaseVerdict.CRITICAL_FAIL:
                critical_failures += 1

            # Track top issues
            if score.critical_failures:
                top_critical.extend([f"[{case.id}] {cf}" for cf in score.critical_failures])
            for f in score.failures:
                if "fabricated" in f.lower() or "hallucinated" in f.lower():
                    top_hallucinations.append(f"[{case.id}] {f}")
                elif "percentage" in f.lower() or "threshold" in f.lower():
                    top_thresholds.append(f"[{case.id}] {f}")
                elif "safety" in f.lower() or "critic" in f.lower():
                    top_safety.append(f"[{case.id}] {f}")

            # Dimension score accumulation
            for d in DIMENSION_NAMES:
                dim_val = score.dimension_scores.get(d, 100.0)
                dim_accumulators[d].append(dim_val)

        # Metamorphic checks on paired cases (MET-001A/B, MET-002A/B, MET-003A/B)
        pairs = [
            ("MET-001A", "MET-001B", "concurrency shift 100->200 VUs"),
            ("MET-002A", "MET-002B", "latency threshold shift 500->1000 ms"),
            ("MET-003A", "MET-003B", "duration shift 5m->10m"),
        ]
        for id_a, id_b, desc in pairs:
            if id_a in scores_by_id and id_b in scores_by_id:
                sc_a = scores_by_id[id_a]
                sc_b = scores_by_id[id_b]
                status_str = "PASS" if sc_a.verdict == sc_b.verdict and sc_a.verdict == CaseVerdict.PASS else "DRIFT/MISMATCH"
                metamorphic_results.append(f"{id_a} vs {id_b} ({desc}): {status_str}")

        # Final average dimensions
        final_dims = {}
        total_case_scores = [cs.overall_score for cs in case_scores]
        for d in DIMENSION_NAMES:
            acc = dim_accumulators[d]
            final_dims[d] = round(sum(acc) / len(acc), 1) if acc else 100.0

        overall_score = round(sum(total_case_scores) / len(total_case_scores), 1) if total_case_scores else 0.0

        return EvaluationSuiteReport(
            total_cases=len(cases),
            passed=passed,
            partial=partial,
            failed=failed,
            critical_failures=critical_failures,
            overall_score=overall_score,
            dimension_scores=final_dims,
            case_scores=case_scores,
            top_critical_failures=top_critical,
            top_hallucinations=top_hallucinations,
            top_threshold_issues=top_thresholds,
            top_safety_issues=top_safety,
            metamorphic_results=metamorphic_results,
        )
