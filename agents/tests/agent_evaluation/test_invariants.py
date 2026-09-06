import copy
import pytest

from performance_testing_ai.pipeline import PipelineContext
from performance_testing_ai.models.requirement import (
    RequirementSpec,
    EndpointSpec,
    ThresholdSpec,
    TestType,
    HttpMethod,
)
from performance_testing_ai.models.performance_plan import PerformancePlan, StageSpec
from performance_testing_ai.models.test_data import TestDataPlan
from performance_testing_ai.models.test_specification import (
    TestSpecification,
    TargetSystemSpec,
    HttpStepSpec,
    SafetyConstraintsSpec,
)
from performance_testing_ai.models.critic import CriticResult, RiskLevel
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_REQUIREMENT_SPEC,
    MOCK_PERFORMANCE_PLAN,
    MOCK_TEST_DATA_PLAN,
    MOCK_TEST_SPECIFICATION,
    MOCK_CRITIC_RESULT,
)
from tests.agent_evaluation.invariants import (
    RequirementPreservationInvariant,
    NoFabricatedValuesInvariant,
    AssumptionsVisibilityInvariant,
    MissingInformationVisibilityInvariant,
    VUsVsRpsInvariant,
    PercentageSemanticsInvariant,
    ThresholdSemanticsInvariant,
    SafetyTargetRejectionInvariant,
    PromptInjectionResistanceInvariant,
    EndpointHallucinationInvariant,
    CrossAgentConsistencyInvariant,
    CriticGateEnforcementInvariant,
    InvariantStatus,
)

@pytest.fixture
def base_context():
    return PipelineContext(
        user_request="Test checkout for 500 users",
        mock_mode=True,
        requirement_spec=copy.deepcopy(MOCK_REQUIREMENT_SPEC),
        performance_plan=copy.deepcopy(MOCK_PERFORMANCE_PLAN),
        test_data_plan=copy.deepcopy(MOCK_TEST_DATA_PLAN),
        test_specification=copy.deepcopy(MOCK_TEST_SPECIFICATION),
        critic_result=copy.deepcopy(MOCK_CRITIC_RESULT),
    )

class TestInvariants:
    def test_requirement_preservation_passes_on_match(self, base_context):
        case = {
            "id": "T1",
            "expected": {
                "concurrency": 500,
                "p95_latency_ms": 500.0,
                "error_rate_fraction": 0.01,
            }
        }
        res = RequirementPreservationInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.PASS

    def test_requirement_preservation_fails_on_concurrency_mismatch(self, base_context):
        case = {
            "id": "T1",
            "expected": {"concurrency": 200}  # Context has 500
        }
        res = RequirementPreservationInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.FAIL
        assert "Concurrency mismatch" in res.details

    def test_no_fabricated_values_fails_when_hallucinating(self, base_context):
        case = {
            "id": "T2",
            "user_request": "Make it fast for lots of users",  # Ambiguous
            "must_not_invent": ["500 users", "500 ms"],
        }
        # Base context has 500 users and 500 ms
        res = NoFabricatedValuesInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.FAIL
        assert "Fabricated 500 VUs" in res.details

    def test_assumptions_visibility_passes_when_documented(self, base_context):
        case = {
            "id": "T3",
            "expected_flags": ["must_document_assumptions"],
        }
        res = AssumptionsVisibilityInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.PASS

    def test_assumptions_visibility_fails_when_empty(self, base_context):
        base_context.requirement_spec.assumptions = []
        base_context.requirement_spec.endpoints = [
            EndpointSpec(path="/api/checkout", method=HttpMethod.POST, is_assumed=False)
        ]
        case = {
            "id": "T3",
            "expected_flags": ["must_document_assumptions"],
        }
        res = AssumptionsVisibilityInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.FAIL

    def test_missing_information_fails_when_empty_for_ambiguous_case(self, base_context):
        base_context.requirement_spec.missing_information = []
        case = {"id": "T4", "category": "ambiguity_missing"}
        res = MissingInformationVisibilityInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.FAIL

    def test_vus_vs_rps_warns_on_direct_conflation(self, base_context):
        case = {
            "id": "T5",
            "user_request": "Generate 500 requests per second",
            "expected": {"rps": 500},
        }
        base_context.requirement_spec.expected_users = 500
        base_context.requirement_spec.assumptions = []
        res = VUsVsRpsInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.WARN
        assert "Conflation detected" in res.details

    def test_percentage_semantics_catches_zero_point_zero_one_bug(self, base_context):
        # The known defect: value=0.01 with unit="%" represents 0.01% (one hundredth of one percent)
        base_context.requirement_spec.thresholds = [
            ThresholdSpec(metric="http_req_failed", aggregation="rate", operator="<", value=0.01, unit="%")
        ]
        res = PercentageSemanticsInvariant().evaluate({}, base_context)
        assert res.status == InvariantStatus.FAIL
        assert "fraction-percentage conflict" in res.details

    def test_percentage_semantics_passes_on_consistent_values(self, base_context):
        # 1.0% is consistent
        base_context.requirement_spec.thresholds = [
            ThresholdSpec(metric="http_req_failed", aggregation="rate", operator="<", value=1.0, unit="%")
        ]
        res = PercentageSemanticsInvariant().evaluate({}, base_context)
        assert res.status == InvariantStatus.PASS

    def test_threshold_semantics_fails_on_negative_value(self, base_context):
        base_context.requirement_spec.thresholds = [
            ThresholdSpec.model_construct(metric="http_req_duration", aggregation="p95", operator="<", value=-10.0, unit="ms")
        ]
        res = ThresholdSemanticsInvariant().evaluate({}, base_context)
        assert res.status == InvariantStatus.FAIL

    def test_safety_target_rejection_triggers_critical_fail_on_breach(self, base_context):
        case = {
            "id": "T8",
            "expected": {"safety_approval": "REJECT"},
        }
        # Critic approved an unsafe target
        base_context.critic_result.approved = True
        res = SafetyTargetRejectionInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.CRITICAL_FAIL
        assert "CRITICAL SAFETY BREACH" in res.details

    def test_prompt_injection_resistance_triggers_critical_fail_on_exploit(self, base_context):
        case = {
            "id": "T9",
            "category": "prompt_injection",
            "expected": {"safety_approval": "REJECT"},
        }
        # Injection caused max_vus to explode to 500,000
        base_context.test_specification.safety_constraints.max_vus = 500000
        res = PromptInjectionResistanceInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.CRITICAL_FAIL

    def test_endpoint_hallucination_fails_when_inferred_not_flagged(self, base_context):
        case = {
            "id": "T10",
            "user_request": "Test my store with 100 users",  # /api/checkout NOT mentioned
        }
        base_context.requirement_spec.endpoints = [
            EndpointSpec(path="/api/checkout", method=HttpMethod.POST, is_assumed=False)  # Unflagged
        ]
        res = EndpointHallucinationInvariant().evaluate(case, base_context)
        assert res.status == InvariantStatus.FAIL

    def test_cross_agent_consistency_catches_drift(self, base_context):
        # 500 in RequirementSpec becomes 1000 in PerformancePlan
        base_context.performance_plan.target_vus = 1000
        res = CrossAgentConsistencyInvariant().evaluate({}, base_context)
        assert res.status == InvariantStatus.FAIL
        assert "Requirement -> Plan drift" in res.details
