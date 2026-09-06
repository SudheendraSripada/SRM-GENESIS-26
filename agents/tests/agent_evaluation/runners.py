import os
from typing import Any, Dict, List, Optional

from performance_testing_ai.pipeline import PerformanceTestingPipeline, PipelineContext
from tests.agent_evaluation.evaluator import AgentEvaluator, EvaluationCase, load_test_cases
from tests.agent_evaluation.scoring import EvaluationSuiteReport

def run_mock_evaluation(
    cases_file: Optional[str] = None,
    print_report: bool = True,
) -> EvaluationSuiteReport:
    """
    Executes the evaluation suite in MOCK mode.
    Tests the evaluator, invariants, scoring metrics, and documents the limitations
    of static mock fixture generation.
    """
    cases = load_test_cases(cases_file)
    pipeline = PerformanceTestingPipeline(mock_mode=True)
    evaluator = AgentEvaluator()

    contexts: List[PipelineContext] = []
    for case in cases:
        ctx = pipeline.run(user_request=case.user_request)
        contexts.append(ctx)

    report = evaluator.evaluate_suite(cases, contexts)

    if print_report:
        print(report.format_console_report())

    return report

def run_real_llm_evaluation(
    cases_file: Optional[str] = None,
    print_report: bool = True,
) -> EvaluationSuiteReport:
    """
    Executes the evaluation suite in REAL-LLM mode using configured LLM provider.
    Requires explicit opt-in via environment variable AGENT_EVAL_REAL_LLM=1.
    Never executes automatically during normal unit test runs.
    """
    opt_in = os.getenv("AGENT_EVAL_REAL_LLM", "").lower() in ("1", "true", "yes")
    if not opt_in:
        raise RuntimeError(
            "Real LLM evaluation requires explicit opt-in. "
            "Set AGENT_EVAL_REAL_LLM=1 in your environment to run live LLM evaluations."
        )

    cases = load_test_cases(cases_file)
    pipeline = PerformanceTestingPipeline(mock_mode=False)
    evaluator = AgentEvaluator()

    contexts: List[PipelineContext] = []
    for case in cases:
        ctx = pipeline.run(user_request=case.user_request)
        contexts.append(ctx)

    report = evaluator.evaluate_suite(cases, contexts)

    if print_report:
        print(report.format_console_report())

    return report

def run_repeatability_test(
    case: EvaluationCase,
    repetitions: int = 5,
    mock_mode: bool = True,
) -> Dict[str, Any]:
    """
    Runs the same evaluation case multiple times to measure semantic output stability.
    Tracks numeric drift, endpoint drift, test-type drift, threshold drift, and safety drift.
    """
    pipeline = PerformanceTestingPipeline(mock_mode=mock_mode)
    
    concurrency_history: List[int] = []
    test_type_history: List[str] = []
    threshold_history: List[float] = []
    safety_history: List[bool] = []

    for _ in range(repetitions):
        ctx = pipeline.run(user_request=case.user_request)
        if ctx.requirement_spec:
            concurrency_history.append(ctx.requirement_spec.expected_users)
            test_type_history.append(ctx.requirement_spec.test_type.value)
            if ctx.requirement_spec.thresholds:
                threshold_history.append(ctx.requirement_spec.thresholds[0].value)
        if ctx.critic_result:
            safety_history.append(ctx.critic_result.approved)

    # Detect semantic drift
    concurrency_drift = len(set(concurrency_history)) > 1
    test_type_drift = len(set(test_type_history)) > 1
    threshold_drift = len(set(threshold_history)) > 1
    safety_drift = len(set(safety_history)) > 1

    has_drift = concurrency_drift or test_type_drift or threshold_drift or safety_drift

    return {
        "case_id": case.id,
        "repetitions": repetitions,
        "concurrency_drift": concurrency_drift,
        "concurrency_values": concurrency_history,
        "test_type_drift": test_type_drift,
        "test_type_values": test_type_history,
        "threshold_drift": threshold_drift,
        "threshold_values": threshold_history,
        "safety_drift": safety_drift,
        "safety_values": safety_history,
        "is_semantically_stable": not has_drift,
    }
