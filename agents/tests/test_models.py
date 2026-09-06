import pytest
from pydantic import ValidationError

from performance_testing_ai.models.requirement import (
    RequirementSpec,
    EndpointSpec,
    ThresholdSpec,
    TestType,
    HttpMethod,
)
from performance_testing_ai.models.performance_plan import (
    PerformancePlan,
    StageSpec,
)
from performance_testing_ai.models.test_data import (
    TestDataPlan,
    DatasetRequirement,
    UserProfileSpec,
    ParameterizationRule,
    SelectionMode,
)
from performance_testing_ai.models.test_specification import (
    TestSpecification,
    TargetSystemSpec,
    HttpStepSpec,
    SafetyConstraintsSpec,
)
from performance_testing_ai.models.critic import (
    CriticResult,
    RiskLevel,
    ValidationCategory,
    ValidationStatus,
    SafetyCheck,
)
from performance_testing_ai.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionMetrics,
    ThresholdResult,
)
from performance_testing_ai.models.analysis_result import (
    AnalysisResult,
    SlaAssessment,
    SlaStatus,
    Observation,
    Hypothesis,
    BottleneckIndicator,
)
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_REQUIREMENT_SPEC,
    MOCK_PERFORMANCE_PLAN,
    MOCK_TEST_DATA_PLAN,
    MOCK_TEST_SPECIFICATION,
    MOCK_CRITIC_RESULT,
    MOCK_EXECUTION_RESULT,
    MOCK_ANALYSIS_RESULT,
)

class TestRequirementSpec:
    def test_valid_spec(self):
        spec = MOCK_REQUIREMENT_SPEC
        assert spec.target_application == "e-commerce application"
        assert spec.expected_users == 500
        assert spec.user_request != ""
        assert len(spec.thresholds) == 2
        assert spec.thresholds[0].value == 500.0
        assert spec.thresholds[0].expression == "http_req_duration(p95) < 500.0ms"
        assert len(spec.assumptions) > 0
        assert len(spec.missing_information) > 0

    def test_invalid_users_raises(self):
        with pytest.raises(ValidationError):
            RequirementSpec(
                user_request="test load",
                target_application="app",
                expected_users=0,  # ge=1 required
            )

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            # Missing user_request and expected_users
            RequirementSpec(
                target_application="app",
            )

    def test_invalid_negative_threshold_raises(self):
        with pytest.raises(ValidationError):
            ThresholdSpec(
                metric="http_req_duration",
                operator="<",
                value=-10.0,  # non-negative required
            )

    def test_invalid_endpoint_path_raises(self):
        with pytest.raises(ValidationError):
            EndpointSpec(path="checkout", method=HttpMethod.POST)  # Must start with /

    def test_endpoint_assumed_flag(self):
        ep = EndpointSpec(path="/checkout", method=HttpMethod.POST, is_assumed=True)
        assert ep.is_assumed is True
        assert ep.method == HttpMethod.POST

class TestPerformancePlan:
    def test_valid_plan(self):
        plan = MOCK_PERFORMANCE_PLAN
        assert plan.target_vus == 500
        assert len(plan.stages) == 3
        assert plan.stages[0].target_vus == 500
        assert plan.ramp_up == "2m"

    def test_invalid_target_vus_raises(self):
        with pytest.raises(ValidationError):
            PerformancePlan(
                plan_id="p1",
                test_type=TestType.LOAD,
                objective="Test load",
                stages=[StageSpec(duration="1m", target_vus=10)],
                target_vus=0,  # ge=1 required
                duration="1m",
            )

    def test_invalid_stage_duration_format_raises(self):
        with pytest.raises(ValidationError):
            StageSpec(duration="100", target_vus=50)  # Must end in s, m, or h

    def test_empty_stages_raises(self):
        with pytest.raises(ValidationError):
            PerformancePlan(
                plan_id="p1",
                test_type=TestType.LOAD,
                objective="Test load",
                stages=[],  # min_length=1 required
                target_vus=100,
                duration="5m",
            )

class TestTestDataPlan:
    def test_valid_data_plan(self):
        data_plan = MOCK_TEST_DATA_PLAN
        assert data_plan.users_required == 500
        assert data_plan.unique_users_required is True
        assert len(data_plan.payload_requirements) > 0
        assert data_plan.data_generation_strategy != ""

    def test_invalid_users_required_raises(self):
        with pytest.raises(ValidationError):
            TestDataPlan(
                data_plan_id="d1",
                plan_id="p1",
                users_required=-5,  # ge=1 required
                data_generation_strategy="mock",
            )

class TestTestSpecification:
    def test_valid_specification(self):
        spec = MOCK_TEST_SPECIFICATION
        assert spec.target.base_url == "http://staging-ecom.local"
        assert len(spec.load) == 3
        assert len(spec.request_sequence) == 1
        assert spec.request_sequence[0].endpoint == "/api/checkout"
        assert spec.safety_constraints.max_vus == 550
        assert spec.safety_constraints.max_duration_seconds == 600

    def test_safety_constraint_boundary_raises(self):
        with pytest.raises(ValidationError):
            SafetyConstraintsSpec(
                max_vus=0,  # ge=1 required
                max_duration_seconds=300,
            )

class TestCriticResult:
    def test_valid_critic_result(self):
        critic = MOCK_CRITIC_RESULT
        assert critic.approved is True
        assert critic.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
        
        categories = {c.category for c in critic.safety_checks}
        assert ValidationCategory.TARGET_VALIDITY in categories
        assert ValidationCategory.LOAD_LEVELS in categories
        assert ValidationCategory.SAFETY_LIMITS in categories
        assert ValidationCategory.USER_OBJECTIVE_ALIGNMENT in categories
        assert len(categories) == 10

class TestExecutionResult:
    def test_valid_execution_result(self):
        exec_res = MOCK_EXECUTION_RESULT
        assert exec_res.status == ExecutionStatus.SUCCESS
        assert exec_res.metrics.requests == 98250
        assert exec_res.metrics.error_rate == 0.0042
        assert exec_res.metrics.p95_ms == 462.8
        assert len(exec_res.thresholds) == 2
        assert all(t.passed for t in exec_res.thresholds)

    def test_invalid_error_rate_percentage_raises(self):
        with pytest.raises(ValidationError):
            ExecutionMetrics(
                requests=100,
                rps=10.0,
                avg_latency_ms=100.0,
                p95_ms=200.0,
                p99_ms=300.0,
                error_rate=1.5,  # le=1.0 required
                iterations=50,
            )

class TestAnalysisResult:
    def test_observation_vs_hypothesis_separation(self):
        analysis = MOCK_ANALYSIS_RESULT
        assert analysis.overall_status == "PASSED"
        assert len(analysis.observations) > 0
        assert len(analysis.hypotheses) > 0

        # Observations must cite empirical facts with evidence
        for obs in analysis.observations:
            assert obs.evidence_source, "Observations must cite empirical evidence"
            assert obs.observed_fact, "Observations must record measurable facts"

        # Hypotheses must clearly require confirming evidence and cannot claim root cause alone
        for hyp in analysis.hypotheses:
            assert hyp.required_evidence_to_confirm, "Hypotheses must specify evidence needed to confirm root cause"
            assert hyp.confidence_level in ("low", "medium", "high")

    def test_confidence_boundary_raises(self):
        with pytest.raises(ValidationError):
            AnalysisResult(
                analysis_id="a1",
                test_id="t1",
                overall_status="PASSED",
                confidence=1.5,  # le=1.0 required
            )
