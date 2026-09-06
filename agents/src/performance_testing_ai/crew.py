from typing import Optional
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from performance_testing_ai.models.requirement import RequirementSpec
from performance_testing_ai.models.performance_plan import PerformancePlan
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.critic import CriticResult
from performance_testing_ai.models.analysis_result import AnalysisResult

from performance_testing_ai.agents.requirement_analyst import create_requirement_analyst_agent
from performance_testing_ai.agents.performance_planner import create_performance_planner_agent
from performance_testing_ai.agents.test_data_agent import create_test_data_agent
from performance_testing_ai.agents.workload_builder import create_workload_builder_agent
from performance_testing_ai.agents.critic_agent import create_critic_agent
from performance_testing_ai.agents.performance_analyst import create_performance_analyst_agent
from performance_testing_ai.llm_config import create_llm

@CrewBase
class PerformanceTestingAiCrew:
    """
    IEEE Genesis Performance Testing Crew.
    Controlled sequential orchestration of 6 specialized agents with strict Pydantic output contracts.
    """

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, llm: Optional[LLM] = None):
        self.llm = llm if llm is not None else create_llm()

    # ------------------ Agents ------------------

    @agent
    def requirement_analyst(self) -> Agent:
        return create_requirement_analyst_agent(
            config=self.agents_config['requirement_analyst'],
            llm=self.llm,
        )

    @agent
    def performance_planner(self) -> Agent:
        return create_performance_planner_agent(
            config=self.agents_config['performance_planner'],
            llm=self.llm,
        )

    @agent
    def test_data_agent(self) -> Agent:
        return create_test_data_agent(
            config=self.agents_config['test_data_agent'],
            llm=self.llm,
        )

    @agent
    def workload_builder(self) -> Agent:
        return create_workload_builder_agent(
            config=self.agents_config['workload_builder'],
            llm=self.llm,
        )

    @agent
    def critic_agent(self) -> Agent:
        return create_critic_agent(
            config=self.agents_config['critic_agent'],
            llm=self.llm,
        )

    @agent
    def performance_analyst(self) -> Agent:
        return create_performance_analyst_agent(
            config=self.agents_config['performance_analyst'],
            llm=self.llm,
        )

    # ------------------ Tasks ------------------

    @task
    def analyze_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_requirements_task'],
            output_pydantic=RequirementSpec,
        )

    @task
    def create_performance_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config['create_performance_plan_task'],
            context=[self.analyze_requirements_task()],
            output_pydantic=PerformancePlan,
        )

    @task
    def plan_test_data_task(self) -> Task:
        return Task(
            config=self.tasks_config['plan_test_data_task'],
            context=[
                self.analyze_requirements_task(),
                self.create_performance_plan_task(),
            ],
            output_pydantic=TestDataPlan,
        )

    @task
    def build_workload_specification_task(self) -> Task:
        return Task(
            config=self.tasks_config['build_workload_specification_task'],
            context=[
                self.analyze_requirements_task(),
                self.create_performance_plan_task(),
                self.plan_test_data_task(),
            ],
            output_pydantic=TestSpecification,
        )

    @task
    def critique_and_validate_safety_task(self) -> Task:
        return Task(
            config=self.tasks_config['critique_and_validate_safety_task'],
            context=[self.build_workload_specification_task()],
            output_pydantic=CriticResult,
        )

    @task
    def analyze_performance_results_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_performance_results_task'],
            context=[self.build_workload_specification_task()],
            output_pydantic=AnalysisResult,
        )

    # ------------------ Crew ------------------

    @crew
    def crew(self) -> Crew:
        """Sequential 6-agent Crew for end-to-end performance testing planning and analysis."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
