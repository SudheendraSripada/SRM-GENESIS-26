import argparse
import os
import pytest
from unittest.mock import MagicMock, patch

from performance_testing_ai.main import parse_args, run
from performance_testing_ai.pipeline import (
    run_pipeline,
    is_mock_mode_enabled,
    PerformanceTestingPipeline,
    PipelineContext,
)
from performance_testing_ai.models.requirement import RequirementSpec
from performance_testing_ai.models.performance_plan import PerformancePlan
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.critic import CriticResult
from performance_testing_ai.llm_config import create_llm, LLMProvider
from performance_testing_ai.crew import PerformanceTestingAiCrew
from performance_testing_ai.fixtures.sample_requests import (
    EXAMPLE_USER_REQUEST,
    MOCK_REQUIREMENT_SPEC,
    MOCK_PERFORMANCE_PLAN,
    MOCK_TEST_DATA_PLAN,
    MOCK_TEST_SPECIFICATION,
    MOCK_CRITIC_RESULT,
)
from crewai.tasks.task_output import TaskOutput
from crewai.crews.crew_output import CrewOutput


class TestCliModeSelection:
    def test_cli_explicit_mock_flag_selects_mock_mode(self, monkeypatch):
        """1. --mock explicitly selects mock mode regardless of env configuration."""
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "false")
        args = parse_args(["--mock"])
        assert args.mock is True

    def test_cli_explicit_no_mock_flag_disables_mock_mode(self, monkeypatch):
        """2. --no-mock explicitly disables mock mode regardless of env configuration."""
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "true")
        args = parse_args(["--no-mock"])
        assert args.mock is False

    def test_cli_neither_flag_respects_env_configuration(self, monkeypatch):
        """3. Neither flag does not force mock mode independently of configuration."""
        args = parse_args([])
        assert args.mock is None  # Does not hardcode True or False

        # When env is false, effective mode is false
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "false")
        assert is_mock_mode_enabled() is False

        # When env is true, effective mode is true
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "true")
        assert is_mock_mode_enabled() is True

    def test_argparse_default_true_bug_cannot_return(self):
        """4. Verify that the previous default=True bug on --mock cannot return."""
        args = parse_args([])
        assert args.mock is not True, "Regressed: --mock default is hardcoded to True!"


class TestPipelineModeExecution:
    def test_mock_mode_works_without_api_keys(self, monkeypatch):
        """5. Mock mode continues to work without any API keys or network requests."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "true")

        ctx = run_pipeline(user_request=EXAMPLE_USER_REQUEST, mock_mode=True)
        assert ctx.mock_mode is True
        assert ctx.requirement_spec is not None
        assert ctx.performance_plan is not None
        assert ctx.test_data_plan is not None
        assert ctx.test_specification is not None
        assert ctx.critic_result is not None
        assert ctx.execution_result is not None
        assert ctx.analysis_result is not None

    def test_live_mode_attempts_llm_construction_when_configured(self, monkeypatch):
        """6. Live mode attempts to construct/use configured LLM when configuration exists."""
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Missing required key in live mode raises clear error
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            create_llm(provider=LLMProvider.OPENAI)

        # Configured local provider (Ollama) constructs LLM without API key
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        llm = create_llm(provider=LLMProvider.OLLAMA)
        assert llm is not None
        assert "llama3.2" in llm.model

    def test_live_crew_result_is_not_discarded(self, monkeypatch):
        """7. The return value of crew.kickoff() is not discarded in live mode."""
        monkeypatch.setenv("PERFORMANCE_TESTING_MOCK_MODE", "false")

        # Create simulated live task outputs
        t1 = TaskOutput(description="Req Task", agent="requirement_analyst", pydantic=MOCK_REQUIREMENT_SPEC)
        t2 = TaskOutput(description="Plan Task", agent="performance_planner", pydantic=MOCK_PERFORMANCE_PLAN)
        t3 = TaskOutput(description="Data Task", agent="test_data_agent", pydantic=MOCK_TEST_DATA_PLAN)
        t4 = TaskOutput(description="Workload Task", agent="workload_builder", pydantic=MOCK_TEST_SPECIFICATION)
        t5 = TaskOutput(description="Critic Task", agent="critic_agent", pydantic=MOCK_CRITIC_RESULT)

        fake_crew_output = CrewOutput(
            raw="Finished live planning",
            tasks_output=[t1, t2, t3, t4, t5],
        )

        dummy_llm = create_llm(provider=LLMProvider.OLLAMA)
        with patch("performance_testing_ai.crew.create_llm", return_value=dummy_llm), \
             patch("crewai.Crew.kickoff", return_value=fake_crew_output):
            pipeline = PerformanceTestingPipeline(mock_mode=False)
            context = pipeline.run(user_request="Live load test requirement")

            # Assert live outputs were captured and NOT left as None
            assert context.mock_mode is False
            assert context.requirement_spec == MOCK_REQUIREMENT_SPEC
            assert context.performance_plan == MOCK_PERFORMANCE_PLAN
            assert context.test_data_plan == MOCK_TEST_DATA_PLAN
            assert context.test_specification == MOCK_TEST_SPECIFICATION
            assert context.critic_result == MOCK_CRITIC_RESULT

    def test_pipeline_does_not_fabricate_execution_result_in_live_mode(self):
        """8. The pipeline does not fabricate ExecutionResult or AnalysisResult in live mode."""
        t1 = TaskOutput(description="Req Task", agent="requirement_analyst", pydantic=MOCK_REQUIREMENT_SPEC)
        fake_crew_output = CrewOutput(raw="Done", tasks_output=[t1])
        dummy_llm = create_llm(provider=LLMProvider.OLLAMA)

        with patch("performance_testing_ai.crew.create_llm", return_value=dummy_llm), \
             patch("crewai.Crew.kickoff", return_value=fake_crew_output):
            pipeline = PerformanceTestingPipeline(mock_mode=False)
            context = pipeline.run(user_request="Live load test")

            # ExecutionResult and AnalysisResult must NOT be fabricated in live path
            assert context.execution_result is None
            assert context.analysis_result is None

    def test_mock_output_identifies_synthetic_execution_data(self, capsys):
        """9. Mock output explicitly warns user that execution and analysis data are simulated."""
        with patch("sys.argv", ["performance-testing-ai", "--mock"]):
            run()

        captured = capsys.readouterr().out
        assert "Mode: MOCK_MODE (No LLM calls)" in captured
        assert "SIMULATED/MOCK data" in captured
        assert "No real performance test has been executed" in captured
