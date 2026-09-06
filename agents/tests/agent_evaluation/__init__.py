"""
Agent Evaluation Package (Phase 3E).
Provides evaluation harnesses, invariant verification, normalization,
and scoring for the six-agent performance-testing pipeline.
"""

from tests.agent_evaluation.normalization import (
    normalize_duration_seconds,
    normalize_latency_ms,
    normalize_error_rate,
    normalize_test_type,
)
from tests.agent_evaluation.invariants import (
    InvariantResult,
    InvariantStatus,
    BaseInvariant,
    ALL_INVARIANTS,
)
from tests.agent_evaluation.scoring import (
    CaseVerdict,
    CaseScore,
    EvaluationSuiteReport,
    calculate_case_score,
)
from tests.agent_evaluation.evaluator import (
    EvaluationCase,
    AgentEvaluator,
    load_test_cases,
)
from tests.agent_evaluation.runners import (
    run_mock_evaluation,
    run_real_llm_evaluation,
    run_repeatability_test,
)

__all__ = [
    "normalize_duration_seconds",
    "normalize_latency_ms",
    "normalize_error_rate",
    "normalize_test_type",
    "InvariantResult",
    "InvariantStatus",
    "BaseInvariant",
    "ALL_INVARIANTS",
    "CaseVerdict",
    "CaseScore",
    "EvaluationSuiteReport",
    "calculate_case_score",
    "EvaluationCase",
    "AgentEvaluator",
    "load_test_cases",
    "run_mock_evaluation",
    "run_real_llm_evaluation",
    "run_repeatability_test",
]
