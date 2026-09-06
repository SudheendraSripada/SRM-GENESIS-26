import os
from typing import Optional
from pydantic import BaseModel, Field

from performance_testing_ai.models.requirement import RequirementSpec
from performance_testing_ai.models.performance_plan import PerformancePlan
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.critic import CriticResult
from performance_testing_ai.models.execution_result import ExecutionResult
from performance_testing_ai.models.analysis_result import AnalysisResult

def is_mock_mode_enabled() -> bool:
    """Check if MOCK_MODE is enabled via environment variable."""
    return os.getenv("PERFORMANCE_TESTING_MOCK_MODE", "true").lower() in ("true", "1", "yes")

class PipelineContext(BaseModel):
    """
    Context container carrying artifacts across all 6 stages of the performance testing pipeline.
    """
    user_request: str = Field(..., description="Original natural language request from user")
    mock_mode: bool = Field(default=True, description="Whether this execution ran in mock mode")
    
    # Stage 1
    requirement_spec: Optional[RequirementSpec] = None
    # Stage 2
    performance_plan: Optional[PerformancePlan] = None
    # Stage 3
    test_data_plan: Optional[TestDataPlan] = None
    # Stage 4
    test_specification: Optional[TestSpecification] = None
    # Stage 5
    critic_result: Optional[CriticResult] = None
    # Execution Layer Output (passed in or simulated)
    execution_result: Optional[ExecutionResult] = None
    # Stage 6
    analysis_result: Optional[AnalysisResult] = None

class PerformanceTestingPipeline:
    """
    Sequential orchestrator for the 6-agent performance-testing pipeline.
    Supports both MOCK_MODE (zero LLM calls/API keys needed) and future live CrewAI execution.
    """

    def __init__(self, mock_mode: Optional[bool] = None):
        self.mock_mode = is_mock_mode_enabled() if mock_mode is None else mock_mode

    def run(
        self,
        user_request: str,
        execution_result: Optional[ExecutionResult] = None,
    ) -> PipelineContext:
        """
        Executes all 6 stages in strict sequential order.
        """
        context = PipelineContext(user_request=user_request, mock_mode=self.mock_mode)

        if self.mock_mode:
            return self._run_mock_pipeline(context, execution_result)
        else:
            return self._run_crewai_pipeline(context, execution_result)

    def _run_mock_pipeline(
        self,
        context: PipelineContext,
        execution_result: Optional[ExecutionResult] = None,
    ) -> PipelineContext:
        """
        Deterministic execution for testing contracts and architecture without LLM calls.
        """
        from performance_testing_ai.fixtures.sample_requests import (
            MOCK_REQUIREMENT_SPEC,
            MOCK_PERFORMANCE_PLAN,
            MOCK_TEST_DATA_PLAN,
            MOCK_TEST_SPECIFICATION,
            MOCK_CRITIC_RESULT,
            MOCK_EXECUTION_RESULT,
            MOCK_ANALYSIS_RESULT,
        )

        # Stage 1: Requirement Analyst
        context.requirement_spec = MOCK_REQUIREMENT_SPEC

        # Stage 2: Performance Planner (consumes requirement_spec)
        context.performance_plan = MOCK_PERFORMANCE_PLAN

        # Stage 3: Test Data Agent (consumes performance_plan & requirement_spec)
        context.test_data_plan = MOCK_TEST_DATA_PLAN

        # Stage 4: Workload Builder (consumes test_data_plan, performance_plan, requirement_spec)
        context.test_specification = MOCK_TEST_SPECIFICATION

        # Stage 5: Critic/Safety Agent (consumes test_specification)
        context.critic_result = MOCK_CRITIC_RESULT

        # Execution layer output
        context.execution_result = execution_result or MOCK_EXECUTION_RESULT

        # Stage 6: Performance Analyst (consumes execution_result & test_specification)
        context.analysis_result = MOCK_ANALYSIS_RESULT

        return context

    def _run_crewai_pipeline(
        self,
        context: PipelineContext,
        execution_result: Optional[ExecutionResult] = None,
    ) -> PipelineContext:
        """
        Live CrewAI orchestration (requires LLM API configuration).
        """
        from performance_testing_ai.crew import PerformanceTestingAiCrew
        crew = PerformanceTestingAiCrew().crew()
        
        # When live execution is invoked with LLM, kickoff executes sequentially
        crew_output = crew.kickoff(inputs={"user_request": context.user_request})

        # Map completed task outputs into PipelineContext
        tasks_output = getattr(crew_output, "tasks_output", None)
        if tasks_output:
            for task_out in tasks_output:
                pydantic_obj = getattr(task_out, "pydantic", None)
                if isinstance(pydantic_obj, RequirementSpec):
                    context.requirement_spec = pydantic_obj
                elif isinstance(pydantic_obj, PerformancePlan):
                    context.performance_plan = pydantic_obj
                elif isinstance(pydantic_obj, TestDataPlan):
                    context.test_data_plan = pydantic_obj
                elif isinstance(pydantic_obj, TestSpecification):
                    context.test_specification = pydantic_obj
                elif isinstance(pydantic_obj, CriticResult):
                    context.critic_result = pydantic_obj
                elif pydantic_obj is None and getattr(task_out, "json_dict", None):
                    jd = task_out.json_dict
                    task_name = (getattr(task_out, "name", "") or getattr(task_out, "description", "")).lower()
                    if "requirement" in task_name:
                        try:
                            context.requirement_spec = RequirementSpec.model_validate(jd)
                        except Exception:
                            pass
                    elif "performance_plan" in task_name or "plan" in task_name:
                        try:
                            context.performance_plan = PerformancePlan.model_validate(jd)
                        except Exception:
                            pass
                    elif "test_data" in task_name or "data" in task_name:
                        try:
                            context.test_data_plan = TestDataPlan.model_validate(jd)
                        except Exception:
                            pass
                    elif "workload" in task_name or "specification" in task_name:
                        try:
                            context.test_specification = TestSpecification.model_validate(jd)
                        except Exception:
                            pass
                    elif "critic" in task_name or "safety" in task_name:
                        try:
                            context.critic_result = CriticResult.model_validate(jd)
                        except Exception:
                            pass

        # Execution layer output: remains absent/None unless explicitly provided
        context.execution_result = execution_result

        # Analysis layer output: remains None in live path
        # (Real performance analysis requires actual k6 execution in Phase 3C/3D)
        context.analysis_result = None

        return context

def run_pipeline(
    user_request: str = (
        "Test whether my e-commerce application can handle 500 concurrent users during checkout. "
        "p95 should stay below 500 ms and errors below 1%."
    ),
    mock_mode: Optional[bool] = None,
    execution_result: Optional[ExecutionResult] = None,
) -> PipelineContext:
    """Convenience entrypoint to execute the performance testing pipeline."""
    pipeline = PerformanceTestingPipeline(mock_mode=mock_mode)
    return pipeline.run(user_request=user_request, execution_result=execution_result)
