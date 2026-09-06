import copy
import pytest

from performance_testing_ai.execution.validator import (
    validate_test_specification,
    parse_duration_seconds,
)
from performance_testing_ai.models.test_specification import (
    TestSpecification,
    TargetSystemSpec,
    HttpStepSpec,
    SafetyConstraintsSpec,
)
from performance_testing_ai.models.performance_plan import StageSpec
from performance_testing_ai.models.requirement import (
    HttpMethod,
    TestType,
    ThresholdSpec,
)
from performance_testing_ai.models.critic import (
    CriticResult,
    RiskLevel,
    ValidationCategory,
    ValidationStatus,
    SafetyCheck,
)
from performance_testing_ai.models.validation_result import (
    ValidationSeverity,
    ValidationErrorCode,
    ValidationResult,
)
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_TEST_SPECIFICATION,
    MOCK_CRITIC_RESULT,
)

# ---------------------------------------------------------------------------
# Duration Parser Tests
# ---------------------------------------------------------------------------

class TestDurationParser:
    def test_valid_durations(self):
        assert parse_duration_seconds("10s") == 10
        assert parse_duration_seconds("2m") == 120
        assert parse_duration_seconds("1h") == 3600
        assert parse_duration_seconds(" 5m ") == 300
        assert parse_duration_seconds("90s") == 90

    def test_invalid_durations_raise(self):
        invalid_durations = [
            "abc",
            "10",
            "0s",
            "-1m",
            "5x",
            "",
            "2.5m",
            "00s",
        ]
        for dur in invalid_durations:
            with pytest.raises(ValueError):
                parse_duration_seconds(dur)

# ---------------------------------------------------------------------------
# Deterministic Validator Tests
# ---------------------------------------------------------------------------

class TestExecutionValidator:
    def test_valid_specification_passes(self):
        """A well-formed specification with approved critic passes validation."""
        result = validate_test_specification(
            spec=MOCK_TEST_SPECIFICATION,
            critic_result=MOCK_CRITIC_RESULT,
        )
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.checks_passed == result.checks_performed
        assert "VALID" in result.summary

    def test_valid_specification_without_critic_passes_with_info(self):
        """Standalone validation without critic result passes but generates an INFO notice."""
        result = validate_test_specification(spec=MOCK_TEST_SPECIFICATION, critic_result=None)
        assert result.valid is True
        assert len(result.errors) == 0
        assert any(w.code == ValidationErrorCode.NO_CRITIC_RESULT.value for w in result.warnings)

    def test_invalid_target_url_missing_scheme(self):
        """Rejects base URLs missing the http/https scheme."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.target.base_url = "staging-ecom.local/api"

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_TARGET_URL.value in result.error_codes

    def test_invalid_target_url_unsupported_scheme(self):
        """Rejects unsupported URL schemes such as ftp://."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.target.base_url = "ftp://staging-ecom.local"

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_TARGET_URL.value in result.error_codes

    def test_invalid_target_url_with_whitespace(self):
        """Rejects URLs containing whitespace."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.target.base_url = "http://staging ecom.local"

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_TARGET_URL.value in result.error_codes

    def test_unauthorized_target_domain(self):
        """Rejects target hostnames not present in allowed_domains."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.target.base_url = "http://evil.example.com"
        spec.safety_constraints.allowed_domains = ["staging-ecom.local", "localhost"]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.UNAUTHORIZED_TARGET_DOMAIN.value in result.error_codes

    def test_domain_spoofing_rejected(self):
        """Rejects domain spoofing attacks like example.com.evil.com and evil-example.com."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.safety_constraints.allowed_domains = ["example.com"]

        # Spoofing via suffix sub-domain
        spec.target.base_url = "http://example.com.evil.com"
        res1 = validate_test_specification(spec)
        assert res1.valid is False
        assert ValidationErrorCode.UNAUTHORIZED_TARGET_DOMAIN.value in res1.error_codes

        # Spoofing via prefix hyphen
        spec.target.base_url = "http://evil-example.com"
        res2 = validate_test_specification(spec)
        assert res2.valid is False
        assert ValidationErrorCode.UNAUTHORIZED_TARGET_DOMAIN.value in res2.error_codes

    def test_safe_subdomain_accepted(self):
        """Accepts legitimate subdomains of allowed domain (e.g. api.example.com for example.com)."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.safety_constraints.allowed_domains = ["example.com"]
        spec.target.base_url = "http://api.example.com"

        result = validate_test_specification(spec)
        assert ValidationErrorCode.UNAUTHORIZED_TARGET_DOMAIN.value not in result.error_codes

    def test_empty_allowed_domains_rejected(self):
        """Rejects specifications with an empty allowed_domains whitelist."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.safety_constraints.allowed_domains = []

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.ALLOWED_DOMAINS_EMPTY.value in result.error_codes

    def test_load_target_exceeds_max_vus(self):
        """Rejects stage load concurrency exceeding safety constraints max_vus."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.safety_constraints.max_vus = 500
        spec.load = [
            StageSpec(duration="2m", target_vus=250),
            StageSpec(duration="5m", target_vus=501),  # Exceeds 500
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.LOAD_TARGET_EXCEEDS_MAX_VUS.value in result.error_codes

    def test_excessive_total_duration_rejected(self):
        """Rejects workloads whose total stage duration exceeds max_duration_seconds."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.safety_constraints.max_duration_seconds = 300  # 5 minutes
        spec.load = [
            StageSpec(duration="4m", target_vus=100),
            StageSpec(duration="3m", target_vus=100),  # Total 7m = 420s > 300s
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.DURATION_EXCEEDS_SAFETY_LIMIT.value in result.error_codes

    def test_invalid_stage_duration_format(self):
        """Rejects stage with invalid duration string."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        # Using model_construct to test bypass/corrupted model defense
        spec.load = [
            StageSpec.model_construct(duration="0s", target_vus=100),
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_STAGE_DURATION.value in result.error_codes

    def test_empty_request_sequence_rejected(self):
        """Rejects specification with an empty request sequence."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.request_sequence = []

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.EMPTY_REQUEST_SEQUENCE.value in result.error_codes

    def test_invalid_request_path(self):
        """Rejects steps with paths not starting with '/' or containing spaces."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.request_sequence = [
            HttpStepSpec.model_construct(
                name="Bad Step",
                endpoint="api/checkout",  # Missing leading /
                method=HttpMethod.POST,
                headers={},
                expected_status_codes=[200],
                think_time_seconds=1.0,
            )
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_REQUEST_PATH.value in result.error_codes

    def test_unsupported_http_method(self):
        """Rejects steps with unsupported HTTP methods."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.request_sequence = [
            HttpStepSpec.model_construct(
                name="Head Step",
                endpoint="/api/status",
                method="CONNECT",  # Unsupported method
                headers={},
                expected_status_codes=[200],
                think_time_seconds=0.5,
            )
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.UNSUPPORTED_HTTP_METHOD.value in result.error_codes

    def test_invalid_threshold_value(self):
        """Rejects threshold with percentage value greater than 100%."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.thresholds = [
            ThresholdSpec(
                metric="http_req_failed",
                aggregation="rate",
                operator="<",
                value=150.0,
                unit="%",
            )
        ]

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.INVALID_THRESHOLD.value in result.error_codes

    def test_request_timeout_exceeds_max_duration(self):
        """Rejects per-request timeout that exceeds total max duration."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        spec.target.timeout_seconds = 700.0
        spec.safety_constraints.max_duration_seconds = 600

        result = validate_test_specification(spec)
        assert result.valid is False
        assert ValidationErrorCode.REQUEST_TIMEOUT_EXCEEDS_LIMIT.value in result.error_codes

    def test_critic_rejection_blocks_validation(self):
        """Unapproved critic result mandates validator failure with CRITIC_GATE_REJECTED."""
        rejected_critic = CriticResult(
            critic_id="crit-rej-1",
            test_id=MOCK_TEST_SPECIFICATION.test_id,
            approved=False,
            risk_level=RiskLevel.CRITICAL,
            issues=["Target domain unauthorized in pre-flight safety check"],
            review_summary="REJECTED: Unauthorized target host.",
        )

        result = validate_test_specification(
            spec=MOCK_TEST_SPECIFICATION,
            critic_result=rejected_critic,
        )
        assert result.valid is False
        assert ValidationErrorCode.CRITIC_GATE_REJECTED.value in result.error_codes

    def test_determinism(self):
        """Same input produces identical output across consecutive runs."""
        res1 = validate_test_specification(MOCK_TEST_SPECIFICATION, MOCK_CRITIC_RESULT)
        res2 = validate_test_specification(MOCK_TEST_SPECIFICATION, MOCK_CRITIC_RESULT)

        assert res1 == res2
        assert res1.model_dump() == res2.model_dump()

    def test_multiple_errors_captured(self):
        """Validator captures multiple independent errors across categories in one pass."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        # 1. Invalid scheme
        spec.target.base_url = "ftp://bad-domain.com"
        # 2. Excessive load
        spec.safety_constraints.max_vus = 100
        spec.load = [StageSpec(duration="10m", target_vus=500)]
        # 3. Empty request sequence
        spec.request_sequence = []

        result = validate_test_specification(spec)
        assert result.valid is False
        assert len(result.errors) >= 3
        codes = result.error_codes
        assert ValidationErrorCode.INVALID_TARGET_URL.value in codes
        assert ValidationErrorCode.LOAD_TARGET_EXCEEDS_MAX_VUS.value in codes
        assert ValidationErrorCode.EMPTY_REQUEST_SEQUENCE.value in codes

    def test_no_mutation_of_input_specification(self):
        """Validator performs read-only inspection and does not mutate the input model."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        original_dump = spec.model_dump()

        _ = validate_test_specification(spec, MOCK_CRITIC_RESULT)

        assert spec.model_dump() == original_dump
