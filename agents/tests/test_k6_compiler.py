import copy
import pytest

from performance_testing_ai.execution.compiler import (
    compile_k6_script,
    CompilationError,
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
from performance_testing_ai.fixtures.sample_requests import (
    MOCK_TEST_SPECIFICATION,
)

# ---------------------------------------------------------------------------
# Golden Fixture for Exact Output Verification
# ---------------------------------------------------------------------------

GOLDEN_SPEC = TestSpecification(
    test_id="spec-golden-test",
    test_name="Golden Spec Test",
    objective="Verify deterministic golden compiler output",
    test_type=TestType.LOAD,
    target=TargetSystemSpec(
        base_url="http://localhost:8000",
        default_headers={"Accept": "application/json"},
        timeout_seconds=5.0,
    ),
    load=[
        StageSpec(duration="30s", target_vus=10),
        StageSpec(duration="30s", target_vus=20),
    ],
    thresholds=[
        ThresholdSpec(
            metric="http_req_duration",
            aggregation="p95",
            operator="<",
            value=250.0,
            unit="ms",
        ),
        ThresholdSpec(
            metric="http_req_failed",
            aggregation="rate",
            operator="<",
            value=0.01,
            unit="%",
        ),
    ],
    request_sequence=[
        HttpStepSpec(
            name="Get Products",
            endpoint="/api/products",
            method=HttpMethod.GET,
            headers={"X-Client": "k6-test"},
            expected_status_codes=[200],
            think_time_seconds=1.0,
        )
    ],
    safety_constraints=SafetyConstraintsSpec(
        max_vus=50,
        max_duration_seconds=120,
        allowed_domains=["localhost"],
    ),
)

# ---------------------------------------------------------------------------
# Phase 3B Compiler Tests
# ---------------------------------------------------------------------------

class TestK6Compiler:
    def test_valid_specification_compiles(self):
        """TEST 1: Valid specification produces standalone valid k6 script string."""
        script = compile_k6_script(MOCK_TEST_SPECIFICATION)

        assert isinstance(script, str)
        assert len(script) > 0
        assert "import http from 'k6/http';" in script
        assert "import { check, sleep } from 'k6';" in script
        assert "export const options = {" in script
        assert "export default function () {" in script

    def test_stage_compilation(self):
        """TEST 2: Compiles stages with exact duration and target concurrency."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.load = [
            StageSpec(duration="30s", target_vus=100),
            StageSpec(duration="30s", target_vus=250),
            StageSpec(duration="30s", target_vus=500),
        ]
        spec.safety_constraints.max_vus = 600

        script = compile_k6_script(spec)

        assert "{ duration: \"30s\", target: 100 }" in script
        assert "{ duration: \"30s\", target: 250 }" in script
        assert "{ duration: \"30s\", target: 500 }" in script

    def test_stage_order_preservation(self):
        """TEST 3: Preserves stage ordering strictly without reordering."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.load = [
            StageSpec(duration="10s", target_vus=100),
            StageSpec(duration="20s", target_vus=250),
            StageSpec(duration="30s", target_vus=500),
        ]
        spec.safety_constraints.max_vus = 600

        script = compile_k6_script(spec)

        pos_100 = script.find("target: 100")
        pos_250 = script.find("target: 250")
        pos_500 = script.find("target: 500")

        assert pos_100 != -1 and pos_250 != -1 and pos_500 != -1
        assert pos_100 < pos_250 < pos_500

    def test_base_url_compilation(self):
        """TEST 4: Compiles exact base URL specified in target configuration."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.target.base_url = "http://localhost:8000"

        script = compile_k6_script(spec)
        assert 'const BASE_URL = "http://localhost:8000";' in script

    def test_request_order_preservation(self):
        """TEST 5: Preserves request sequence order in generated default function."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = [
            HttpStepSpec(name="Step 1", endpoint="/products", method=HttpMethod.GET),
            HttpStepSpec(name="Step 2", endpoint="/products/1", method=HttpMethod.GET),
            HttpStepSpec(name="Step 3", endpoint="/cart", method=HttpMethod.POST),
            HttpStepSpec(name="Step 4", endpoint="/checkout", method=HttpMethod.POST),
        ]

        script = compile_k6_script(spec)

        p1 = script.find('BASE_URL + "/products"')
        p2 = script.find('BASE_URL + "/products/1"')
        p3 = script.find('BASE_URL + "/cart"')
        p4 = script.find('BASE_URL + "/checkout"')

        assert p1 != -1 and p2 != -1 and p3 != -1 and p4 != -1
        assert p1 < p2 < p3 < p4

    def test_http_method_mapping(self):
        """TEST 6: Maps GET, POST, PUT, PATCH, DELETE to correct k6 API calls."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = [
            HttpStepSpec(name="Get Step", endpoint="/items", method=HttpMethod.GET),
            HttpStepSpec(name="Post Step", endpoint="/items", method=HttpMethod.POST),
            HttpStepSpec(name="Put Step", endpoint="/items/1", method=HttpMethod.PUT),
            HttpStepSpec(name="Patch Step", endpoint="/items/1", method=HttpMethod.PATCH),
            HttpStepSpec(name="Del Step", endpoint="/items/1", method=HttpMethod.DELETE),
        ]

        script = compile_k6_script(spec)

        assert "http.get(" in script
        assert "http.post(" in script
        assert "http.put(" in script
        assert "http.patch(" in script
        assert "http.del(" in script  # k6 uses http.del for DELETE

    def test_threshold_compilation(self):
        """TEST 7: Compiles latency percentiles and error rates into valid k6 syntax."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.thresholds = [
            ThresholdSpec(metric="http_req_duration", aggregation="p95", operator="<", value=500.0, unit="ms"),
            ThresholdSpec(metric="http_req_duration", aggregation="p99", operator="<", value=1000.0, unit="ms"),
            ThresholdSpec(metric="http_req_failed", aggregation="rate", operator="<", value=0.01, unit="rate"),
        ]

        script = compile_k6_script(spec)

        assert '"http_req_duration": ["p(95)<500", "p(99)<1000"]' in script
        assert '"http_req_failed": ["rate<0.01"]' in script

    def test_threshold_percentage_normalization(self):
        """TEST 7b: Normalizes error rate percentage > 1% (e.g. 5%) to rate fraction (0.05)."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.thresholds = [
            ThresholdSpec(metric="http_req_failed", aggregation="rate", operator="<", value=5.0, unit="%"),
        ]

        script = compile_k6_script(spec)
        assert '"http_req_failed": ["rate<0.05"]' in script

    def test_request_payload_compilation(self):
        """TEST 8: Compiles request payload when payload_schema is present; passes null when absent."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = [
            HttpStepSpec(
                name="Submit Order",
                endpoint="/orders",
                method=HttpMethod.POST,
                payload_schema={"item_id": "123", "qty": "2"},
            ),
            HttpStepSpec(
                name="Empty Post",
                endpoint="/ping",
                method=HttpMethod.POST,
                payload_schema=None,
            ),
        ]

        script = compile_k6_script(spec)

        assert "const payload = JSON.stringify(" in script
        assert '"item_id": "123"' in script
        assert "http.post(BASE_URL + \"/ping\", null, params)" in script

    def test_header_merging_and_compilation(self):
        """TEST 9: Merges target default headers with step-specific headers deterministically."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.target.default_headers = {"User-Agent": "Genesis-PT/1.0", "Content-Type": "application/json"}
        spec.request_sequence = [
            HttpStepSpec(
                name="Auth Request",
                endpoint="/secure",
                method=HttpMethod.GET,
                headers={"Authorization": "Bearer secret-token"},
            )
        ]

        script = compile_k6_script(spec)

        assert '"User-Agent": "Genesis-PT/1.0"' in script
        assert '"Content-Type": "application/json"' in script
        assert '"Authorization": "Bearer secret-token"' in script

    def test_status_code_checks(self):
        """TEST 10: Generates k6 check() assertions for single and multiple status codes."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = [
            HttpStepSpec(name="Single Check", endpoint="/a", method=HttpMethod.GET, expected_status_codes=[200]),
            HttpStepSpec(name="Multi Check", endpoint="/b", method=HttpMethod.POST, expected_status_codes=[200, 201]),
        ]

        script = compile_k6_script(spec)

        assert '"status is 200": (r) => r.status === 200' in script
        assert '"status is 200 or 201": (r) => [200, 201].includes(r.status)' in script

    def test_timeout_compilation(self):
        """TEST 11: Compiles per-request timeout into params.timeout."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.target.timeout_seconds = 15.0

        script = compile_k6_script(spec)
        assert '"timeout": "15s"' in script

    def test_invalid_base_url_raises_compilation_error(self):
        """TEST 12: Rejects invalid base URLs without attempting auto-fix."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.target.base_url = "ftp://invalid-url.com"

        with pytest.raises(CompilationError, match="target.base_url.*is invalid"):
            compile_k6_script(spec)

    def test_no_mutation(self):
        """TEST 13: Compiling does not mutate the input TestSpecification."""
        spec = copy.deepcopy(MOCK_TEST_SPECIFICATION)
        original_dump = spec.model_dump()

        _ = compile_k6_script(spec)

        assert spec.model_dump() == original_dump

    def test_determinism(self):
        """TEST 14: Compiling the same spec twice produces byte-for-byte identical output."""
        script1 = compile_k6_script(MOCK_TEST_SPECIFICATION)
        script2 = compile_k6_script(MOCK_TEST_SPECIFICATION)

        assert script1 == script2
        assert len(script1) > 0

    def test_javascript_string_escaping(self):
        """TEST 15: Securely escapes single quotes, double quotes, newlines, and backslashes."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = [
            HttpStepSpec(
                name="Tricky O'Reilly \"Quotes\"\nNewline and \\slash",
                endpoint="/api/search",
                method=HttpMethod.GET,
                headers={"X-Search": "O'Reilly \"test\"\n"},
            )
        ]

        script = compile_k6_script(spec)

        # Confirm comment newline stripped
        assert "Newline and \\slash" in script
        # Confirm header string escaped via json.dumps
        assert '"X-Search": "O\'Reilly \\"test\\"\\n"' in script

    def test_no_timestamps_or_randomness(self):
        """TEST 16: Multiple compilations contain no changing timestamps or UUIDs."""
        runs = [compile_k6_script(MOCK_TEST_SPECIFICATION) for _ in range(5)]
        assert all(s == runs[0] for s in runs)

    def test_custom_target_reflected(self):
        """TEST 17: Compiles arbitrary custom target URL rather than a hardcoded demo URL."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.target.base_url = "https://custom-service.internal.corp"

        script = compile_k6_script(spec)
        assert 'const BASE_URL = "https://custom-service.internal.corp";' in script

    def test_no_invented_requests(self):
        """TEST 18: Output contains exactly the HTTP calls defined in request_sequence."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        assert len(spec.request_sequence) == 1

        script = compile_k6_script(spec)
        # Exactly one http call
        get_count = script.count("http.get(")
        post_count = script.count("http.post(")
        assert get_count == 1
        assert post_count == 0

    def test_empty_request_sequence_rejected(self):
        """TEST 19: Rejects specification with empty request_sequence."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.request_sequence = []

        with pytest.raises(CompilationError, match="request_sequence is empty"):
            compile_k6_script(spec)

    def test_invalid_stage_rejected(self):
        """TEST 20: Rejects stage with invalid duration string."""
        spec = copy.deepcopy(GOLDEN_SPEC)
        spec.load = [StageSpec.model_construct(duration="0s", target_vus=10)]

        with pytest.raises(CompilationError, match="duration '0s' is invalid"):
            compile_k6_script(spec)

    def test_golden_output_match(self):
        """TEST 21: Compares generated output of GOLDEN_SPEC against expected structure."""
        script = compile_k6_script(GOLDEN_SPEC)

        expected_elements = [
            "import http from 'k6/http';",
            "import { check, sleep } from 'k6';",
            'const BASE_URL = "http://localhost:8000";',
            "export const options = {",
            '        { duration: "30s", target: 10 },',
            '        { duration: "30s", target: 20 },',
            '"http_req_duration": ["p(95)<250"]',
            '"http_req_failed": ["rate<0.01"]',
            "export default function () {",
            "// Step 1: Get Products",
            'http.get(BASE_URL + "/api/products", params)',
            '"status is 200": (r) => r.status === 200',
            "sleep(1);",
        ]

        for elem in expected_elements:
            assert elem in script, f"Missing expected element in golden script: {elem}"
