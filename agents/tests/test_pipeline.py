import copy
import os
import pytest
import yaml

from performance_testing_ai.pipeline import run_pipeline, PerformanceTestingPipeline
from performance_testing_ai.models.requirement import RequirementSpec
from performance_testing_ai.models.performance_plan import PerformancePlan, StageSpec
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.models.test_specification import TestSpecification, TargetSystemSpec
from performance_testing_ai.models.critic import CriticResult, RiskLevel
from performance_testing_ai.models.execution_result import ExecutionResult
from performance_testing_ai.models.analysis_result import AnalysisResult
from performance_testing_ai.agents.critic_agent import evaluate_safety
from performance_testing_ai.crew import PerformanceTestingAiCrew
from performance_testing_ai.llm_config import (
    create_llm,
    get_configured_provider,
    is_mock_mode,
    LLMProvider,
)
from performance_testing_ai.fixtures.sample_requests import (
    EXAMPLE_USER_REQUEST,
    MOCK_TEST_SPECIFICATION,
)

def test_pipeline_runs_in_mock_mode_without_api_keys(monkeypatch):
    """
    Verify that the entire sequential pipeline completes and returns all 6 stage contracts
    without requiring OPENAI_API_KEY, GEMINI_API_KEY, or any external network calls.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    ctx = run_pipeline(user_request=EXAMPLE_USER_REQUEST, mock_mode=True)

    assert ctx.mock_mode is True
    assert ctx.user_request == EXAMPLE_USER_REQUEST

    # Check Stage 1: RequirementSpec
    assert isinstance(ctx.requirement_spec, RequirementSpec)
    assert ctx.requirement_spec.expected_users == 500
    assert ctx.requirement_spec.target_application == "e-commerce application"
    assert len(ctx.requirement_spec.thresholds) == 2

    # Check Stage 2: PerformancePlan
    assert isinstance(ctx.performance_plan, PerformancePlan)
    assert ctx.performance_plan.target_vus == 500
    assert len(ctx.performance_plan.stages) == 3

    # Check Stage 3: TestDataPlan
    assert isinstance(ctx.test_data_plan, TestDataPlan)
    assert ctx.test_data_plan.plan_id == ctx.performance_plan.plan_id
    assert ctx.test_data_plan.users_required == 500

    # Check Stage 4: TestSpecification
    assert isinstance(ctx.test_specification, TestSpecification)
    assert ctx.test_specification.test_id == "spec-ecom-500vu"
    assert len(ctx.test_specification.request_sequence) > 0

    # Check Stage 5: CriticResult
    assert isinstance(ctx.critic_result, CriticResult)
    assert ctx.critic_result.test_id == ctx.test_specification.test_id
    assert ctx.critic_result.approved is True

    # Check Execution Layer Contract
    assert isinstance(ctx.execution_result, ExecutionResult)
    assert ctx.execution_result.test_id == ctx.test_specification.test_id

    # Check Stage 6: AnalysisResult
    assert isinstance(ctx.analysis_result, AnalysisResult)
    assert ctx.analysis_result.test_id == ctx.execution_result.test_id
    assert ctx.analysis_result.overall_status == "PASSED"

def test_contract_continuity_across_stages():
    """
    Verify that each stage safely consumes and references preceding stage artifacts.
    """
    pipeline = PerformanceTestingPipeline(mock_mode=True)
    ctx = pipeline.run(user_request=EXAMPLE_USER_REQUEST)

    # Concurrency alignment: Requirement -> Plan -> Spec Safety
    req_users = ctx.requirement_spec.expected_users
    plan_concurrency = ctx.performance_plan.target_vus
    spec_max_vus = ctx.test_specification.safety_constraints.max_vus
    assert plan_concurrency == req_users
    assert spec_max_vus >= plan_concurrency

    # Critic evaluated all required categories
    checked_categories = {c.category for c in ctx.critic_result.safety_checks}
    assert len(checked_categories) == 10

    # Performance Analyst distinguished observations from hypotheses
    assert len(ctx.analysis_result.observations) > 0
    assert len(ctx.analysis_result.hypotheses) > 0
    for hyp in ctx.analysis_result.hypotheses:
        assert hyp.required_evidence_to_confirm

def test_critic_approves_valid_specification():
    """
    Verify that the safety critic engine approves a well-formed specification within bounds.
    """
    result = evaluate_safety(MOCK_TEST_SPECIFICATION)
    assert result.approved is True
    assert result.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert len(result.issues) == 0

def test_critic_rejects_unauthorized_target_domain():
    """
    Verify that the safety critic rejects a specification targeting an unauthorized domain.
    """
    unsafe_spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
    unsafe_spec.target = TargetSystemSpec(base_url="https://production-payment-gateway.external.com")

    result = evaluate_safety(unsafe_spec)
    assert result.approved is False
    assert result.risk_level == RiskLevel.CRITICAL
    assert any("not in allowed" in issue for issue in result.issues)
    assert len(result.required_changes) > 0

def test_critic_rejects_excessive_load():
    """
    Verify that the safety critic rejects a workload schedule exceeding hard safety limits.
    """
    unsafe_spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
    # Target safety max is 550 VUs; add an excessive 5000 VU stage
    unsafe_spec.load = [StageSpec(duration="10m", target_vus=5000)]

    result = evaluate_safety(unsafe_spec)
    assert result.approved is False
    assert any("exceeds safety limit" in issue for issue in result.issues)

def test_critic_rejects_empty_request_sequence():
    """
    Verify that the safety critic rejects an empty request sequence with no executable steps.
    """
    empty_spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
    empty_spec.request_sequence = []

    result = evaluate_safety(empty_spec)
    assert result.approved is False
    assert any("Request sequence is empty" in issue for issue in result.issues)

def test_crewai_scaffold_initialization_without_api_key(monkeypatch):
    """
    Verify that the CrewAI crew class and its 6 agents and tasks can be cleanly instantiated
    without an API key present in the environment.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "true")

    crew_wrapper = PerformanceTestingAiCrew()
    crew_instance = crew_wrapper.crew()

    assert len(crew_instance.agents) == 6
    assert len(crew_instance.tasks) == 6

    # Verify agent roles are defined and match updated prompts
    roles = [a.role.strip() for a in crew_instance.agents]
    assert any("Requirements Analyst" in r for r in roles)
    assert any("Performance Test Strategist" in r for r in roles)
    assert any("Test Data & State Management" in r for r in roles)
    assert any("Workload Specification Architect" in r for r in roles)
    assert any("Critic" in r for r in roles)
    assert any("Performance Diagnostics & Reliability" in r for r in roles)

    # Verify strict safety boundary: NO execution tools attached to any agent
    for agent in crew_instance.agents:
        assert len(agent.tools) == 0, f"Agent {agent.role} must not have execution tools attached!"
        assert agent.allow_delegation is False

def test_task_context_dependencies_and_output_models():
    """
    Verify sequential contract chaining: each task explicitly references prior task outputs as context
    and binds the exact expected Pydantic model.
    """
    crew_wrapper = PerformanceTestingAiCrew()
    tasks = crew_wrapper.crew().tasks

    # Task 1: analyze_requirements_task
    assert tasks[0].output_pydantic == RequirementSpec

    # Task 2: create_performance_plan_task consumes task 1
    assert tasks[1].output_pydantic == PerformancePlan
    assert isinstance(tasks[1].context, list)
    assert len(tasks[1].context) == 1

    # Task 3: plan_test_data_task consumes tasks 1 & 2
    assert tasks[2].output_pydantic == TestDataPlan
    assert isinstance(tasks[2].context, list)
    assert len(tasks[2].context) == 2

    # Task 4: build_workload_specification_task consumes tasks 1, 2, & 3
    assert tasks[3].output_pydantic == TestSpecification
    assert isinstance(tasks[3].context, list)
    assert len(tasks[3].context) == 3

    # Task 5: critique_and_validate_safety_task consumes task 4
    assert tasks[4].output_pydantic == CriticResult
    assert isinstance(tasks[4].context, list)
    assert len(tasks[4].context) == 1

    # Task 6: analyze_performance_results_task consumes task 4 (spec)
    assert tasks[5].output_pydantic == AnalysisResult
    assert isinstance(tasks[5].context, list)
    assert len(tasks[5].context) == 1

def test_yaml_configurations_valid():
    """
    Verify that agents.yaml and tasks.yaml exist, parse as valid YAML, and contain all 6 definitions.
    """
    agents_path = os.path.join("src", "performance_testing_ai", "config", "agents.yaml")
    tasks_path = os.path.join("src", "performance_testing_ai", "config", "tasks.yaml")

    assert os.path.exists(agents_path)
    assert os.path.exists(tasks_path)

    with open(agents_path, "r", encoding="utf-8") as f:
        agents = yaml.safe_load(f)
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = yaml.safe_load(f)

    expected_agents = [
        "requirement_analyst",
        "performance_planner",
        "test_data_agent",
        "workload_builder",
        "critic_agent",
        "performance_analyst",
    ]
    expected_tasks = [
        "analyze_requirements_task",
        "create_performance_plan_task",
        "plan_test_data_task",
        "build_workload_specification_task",
        "critique_and_validate_safety_task",
        "analyze_performance_results_task",
    ]

    for a in expected_agents:
        assert a in agents, f"Agent '{a}' missing from agents.yaml"
        assert agents[a]["role"], f"Role missing for '{a}'"
        assert agents[a]["goal"], f"Goal missing for '{a}'"
        assert agents[a]["backstory"], f"Backstory missing for '{a}'"

    for t in expected_tasks:
        assert t in tasks, f"Task '{t}' missing from tasks.yaml"
        assert tasks[t]["description"], f"Description missing for '{t}'"
        assert tasks[t]["expected_output"], f"Expected output missing for '{t}'"
        assert tasks[t]["agent"] in expected_agents

def test_llm_config_providers(monkeypatch):
    """
    Verify the LLM provider configuration abstraction.
    In MOCK_MODE, returns None without error.
    Live providers validate API keys and raise informative ValueErrors when missing.
    """
    # MOCK mode
    monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "true")
    assert is_mock_mode() is True
    assert get_configured_provider() == LLMProvider.MOCK
    assert create_llm() is None

    # Missing API key validation for OpenAI
    monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        create_llm(provider=LLMProvider.OPENAI)

    # Missing API key validation for Gemini
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        create_llm(provider=LLMProvider.GEMINI)

    # Missing API key validation for Anthropic
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        create_llm(provider=LLMProvider.ANTHROPIC)

    # Ollama provider does not require API key
    ollama_llm = create_llm(provider=LLMProvider.OLLAMA)
    assert ollama_llm is not None
