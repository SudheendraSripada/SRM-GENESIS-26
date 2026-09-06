#!/usr/bin/env python
import argparse
import json
import sys
from typing import Optional, List
from dotenv import load_dotenv

from performance_testing_ai.pipeline import run_pipeline, is_mock_mode_enabled

load_dotenv()

def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Performance Testing AI - IEEE Genesis Pipeline")
    parser.add_argument(
        "--request",
        type=str,
        default=(
            "Test whether my e-commerce application can handle 500 concurrent users during checkout. "
            "p95 should stay below 500 ms and errors below 1%."
        ),
        help="Natural language performance testing request",
    )
    parser.add_argument(
        "--mock",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run in MOCK_MODE without calling external LLMs or requiring API keys (or --no-mock for live mode)",
    )
    return parser.parse_args(args)

def run() -> None:
    """
    Main entry point for running the Performance Testing AI pipeline.
    """
    args = parse_args()

    # Determine effective mode:
    # Precedence: Explicit CLI flag (--mock / --no-mock) -> Environment variable -> Default (True)
    if args.mock is not None:
        effective_mock = args.mock
    else:
        effective_mock = is_mock_mode_enabled()

    print("=" * 60)
    print(" Performance Testing AI - 6-Agent Sequential Pipeline")
    print(f" Mode: {'MOCK_MODE (No LLM calls)' if effective_mock else 'LIVE CREW'}")
    print("=" * 60)
    print(f"User Request: {args.request}\n")

    result = run_pipeline(user_request=args.request, mock_mode=effective_mock)

    if result.requirement_spec:
        print("[Stage 1] RequirementSpec Generated:")
        print(f"  Target Application: {result.requirement_spec.target_application}")
        print(f"  Target Concurrency: {result.requirement_spec.expected_users} VUs")
        print(f"  Thresholds: {[t.expression for t in result.requirement_spec.thresholds]}")
        print(f"  Assumptions: {result.requirement_spec.assumptions}")
        print(f"  Missing Info: {result.requirement_spec.missing_information}\n")

    if result.performance_plan:
        print("[Stage 2] PerformancePlan Generated:")
        print(f"  Plan ID: {result.performance_plan.plan_id}")
        print(f"  Test Type: {result.performance_plan.test_type}")
        print(f"  Stages: {len(result.performance_plan.stages)} stages ({[s.duration for s in result.performance_plan.stages]})\n")

    if result.test_data_plan:
        print("[Stage 3] TestDataPlan Generated:")
        print(f"  Datasets: {[d.name for d in result.test_data_plan.datasets_needed]}")
        print(f"  User Profiles: {[p.role for p in result.test_data_plan.user_profiles]}\n")

    if result.test_specification:
        print("[Stage 4] TestSpecification Generated:")
        print(f"  Spec Title: {result.test_specification.title}")
        print(f"  Scenarios: {[s.name for s in result.test_specification.scenarios]}")
        print(f"  Safety Max VUs: {result.test_specification.safety_constraints.max_vus} VUs\n")

    if result.critic_result:
        print("[Stage 5] CriticResult Generated:")
        print(f"  Approved: {result.critic_result.is_approved}")
        print(f"  Risk Level: {result.critic_result.risk_level.value.upper()}")
        print(f"  Validation Checks Passed: {sum(1 for c in result.critic_result.validation_checks if c.status == 'pass')}/{len(result.critic_result.validation_checks)}\n")

    if result.analysis_result:
        print("[Stage 6] AnalysisResult Generated:")
        if result.mock_mode:
            print("  NOTE: Execution metrics and analysis shown below are SIMULATED/MOCK data. No real performance test has been executed.")
        print(f"  Overall SLA Met: {result.analysis_result.overall_sla_met}")
        print(f"  Observations: {len(result.analysis_result.observations)} empirical facts recorded")
        print(f"  Hypotheses: {len(result.analysis_result.hypotheses)} hypotheses requiring verification\n")
    else:
        print("[Stage 6] AnalysisResult:")
        print("  NOTE: Live performance execution (k6) has not been run yet. No ExecutionResult or AnalysisResult fabricated.\n")

    print("=" * 60)
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    run()
