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
    DataStrategy,
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
from performance_testing_ai.agents.critic_agent import evaluate_safety

EXAMPLE_USER_REQUEST = (
    "Test whether my e-commerce application can handle 500 concurrent users during checkout. "
    "p95 should stay below 500 ms and errors below 1%."
)

MOCK_REQUIREMENT_SPEC = RequirementSpec(
    user_request=EXAMPLE_USER_REQUEST,
    target_application="e-commerce application",
    target_base_url="http://staging-ecom.local",
    endpoints=[
        EndpointSpec(
            path="/api/checkout",
            method=HttpMethod.POST,
            is_assumed=True,
            description="Assumed checkout submission endpoint based on 'checkout' requirement",
        )
    ],
    expected_users=500,
    duration="8m",
    test_type=TestType.STRESS,
    performance_goals=[
        "Handle 500 concurrent users during checkout",
        "p95 latency below 500 ms",
        "Error rate below 1%",
    ],
    thresholds=[
        ThresholdSpec(
            metric="http_req_duration",
            aggregation="p95",
            operator="<",
            value=500.0,
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
    assumptions=[
        "Target test environment is staging-ecom.local",
        "Duration assumed to be 8-minute ramp and steady window",
        "Checkout involves a POST request to /api/checkout",
    ],
    missing_information=[
        "Exact API checkout request payload schema and authentication mechanism",
    ],
)

MOCK_PERFORMANCE_PLAN = PerformancePlan(
    plan_id="plan-ecom-500vu",
    test_type=TestType.STRESS,
    objective="Verify system stability and SLA compliance at 500 concurrent users on checkout",
    stages=[
        StageSpec(duration="2m", target_vus=500, description="Ramp up from 0 to 500 VUs"),
        StageSpec(duration="5m", target_vus=500, description="Steady state load at 500 VUs"),
        StageSpec(duration="1m", target_vus=0, description="Ramp down to 0 VUs"),
    ],
    ramp_up="2m",
    steady_state="5m",
    ramp_down="1m",
    target_vus=500,
    duration="8m",
    thresholds=MOCK_REQUIREMENT_SPEC.thresholds,
    success_criteria=[
        "p95 latency stays below 500ms at 500 VUs",
        "Error rate stays below 1% throughout test",
    ],
    assumptions=[
        "Staging backend database connection pool is sized for at least 500 connections",
    ],
)

MOCK_TEST_DATA_PLAN = TestDataPlan(
    data_plan_id="data-plan-ecom-500vu",
    plan_id=MOCK_PERFORMANCE_PLAN.plan_id,
    users_required=500,
    unique_users_required=True,
    payload_requirements=["JSON payload with cart_id and payment_token"],
    product_data_requirements=["1000 pre-seeded active carts with 1-3 items"],
    authentication_requirements=["OAuth2 Bearer token per virtual user session"],
    correlation_requirements=["cart_id extracted from session and bound to checkout payload"],
    data_generation_strategy="Pre-seeded staging database customer pool with unique credentials",
    assumptions=["Test database is pre-populated prior to test execution"],
    datasets_needed=[
        DatasetRequirement(
            name="checkout_customers",
            description="Customer accounts with pre-loaded carts",
            volume_needed=1000,
            fields=["user_id", "auth_token", "cart_id"],
            strategy=DataStrategy.PRE_SEEDED,
            is_sensitive=False,
        )
    ],
    user_profiles=[
        UserProfileSpec(
            role="shopper",
            count=500,
            auth_required=True,
            credentials_source="staging_user_pool",
        )
    ],
    parameterization_rules=[
        ParameterizationRule(
            parameter_name="cart_id",
            source_dataset="checkout_customers",
            selection_mode=SelectionMode.UNIQUE,
        )
    ],
)

MOCK_TEST_SPECIFICATION = TestSpecification(
    test_id="spec-ecom-500vu",
    test_name="E-Commerce Checkout 500 VU Concurrency Test",
    objective="Evaluate checkout response time and error rate under 500 concurrent users",
    test_type=TestType.STRESS,
    target=TargetSystemSpec(
        base_url="http://staging-ecom.local",
        default_headers={"Content-Type": "application/json", "User-Agent": "Genesis-PT/1.0"},
        timeout_seconds=10.0,
    ),
    load=MOCK_PERFORMANCE_PLAN.stages,
    thresholds=MOCK_REQUIREMENT_SPEC.thresholds,
    data_requirements=["1000 unique shopper accounts", "Pre-seeded carts"],
    authentication_requirements=["OAuth2 Bearer token per user profile"],
    request_sequence=[
        HttpStepSpec(
            name="Submit Checkout",
            endpoint="/api/checkout",
            method=HttpMethod.POST,
            headers={"Authorization": "Bearer ${auth_token}"},
            payload_schema={"cart_id": "string", "payment_token": "string"},
            expected_status_codes=[200, 201],
            think_time_seconds=1.5,
        )
    ],
    success_criteria=[
        "http_req_duration(p95) < 500ms",
        "http_req_failed(rate) < 0.01",
    ],
    assumptions=["Staging environment is isolated from production traffic"],
    safety_constraints=SafetyConstraintsSpec(
        max_vus=550,
        max_duration_seconds=600,
        allowed_domains=["staging-ecom.local", "localhost", "127.0.0.1"],
        max_rps=1000,
    ),
)

# Deterministically evaluated by the safety critic rule engine
MOCK_CRITIC_RESULT = evaluate_safety(MOCK_TEST_SPECIFICATION)

MOCK_EXECUTION_RESULT = ExecutionResult(
    test_id=MOCK_TEST_SPECIFICATION.test_id,
    status=ExecutionStatus.SUCCESS,
    start_time="2026-09-05T20:00:00Z",
    end_time="2026-09-05T20:08:00Z",
    metrics=ExecutionMetrics(
        requests=98250,
        rps=204.6,
        avg_latency_ms=210.4,
        p95_ms=462.8,
        p99_ms=780.3,
        error_rate=0.0042,  # 0.42% < 1%
        iterations=49125,
    ),
    thresholds=[
        ThresholdResult(
            metric="http_req_duration(p95)",
            threshold_expression="< 500ms",
            actual_value=462.8,
            passed=True,
        ),
        ThresholdResult(
            metric="http_req_failed(rate)",
            threshold_expression="< 1%",
            actual_value=0.0042,
            passed=True,
        ),
    ],
    errors=[],
    raw_summary_reference="reports/exec-ecom-500vu-summary.json",
)

MOCK_ANALYSIS_RESULT = AnalysisResult(
    analysis_id="analysis-ecom-500vu",
    test_id=MOCK_TEST_SPECIFICATION.test_id,
    overall_status="PASSED",
    observations=[
        Observation(
            metric_or_signal="http_req_duration(p95)",
            observed_fact="p95 response time reached 462.8 ms at peak 500 VUs",
            evidence_source="metrics.p95_ms",
        ),
        Observation(
            metric_or_signal="http_req_duration(p99)",
            observed_fact="p99 tail latency jumped to 780.3 ms with maximum latency of 1450.0 ms",
            evidence_source="metrics.p99_ms",
        ),
        Observation(
            metric_or_signal="http_req_failed",
            observed_fact="412 failures recorded out of 98,250 requests (0.42% error rate)",
            evidence_source="metrics.error_rate",
        ),
    ],
    threshold_results=MOCK_EXECUTION_RESULT.thresholds,
    performance_findings=[
        "500 concurrent checkout users handled successfully within all defined SLAs",
        "p95 response time of 462.8 ms satisfies the < 500 ms objective",
        "Error rate of 0.42% satisfies the < 1% objective",
    ],
    possible_bottlenecks=[
        BottleneckIndicator(
            suspected_component="Database connection pool / transaction lock waits",
            evidence="Tail latency amplification (p99 780ms vs avg 210ms) during peak load",
            severity="minor",
        )
    ],
    degradation_point="None observed up to 500 VUs",
    recommendations=[
        "System is approved for 500 concurrent checkout users",
        "Execute a stress test (scaling to 750 VUs) to discover the true system breakpoint",
    ],
    confidence=0.95,
    limitations=[
        "Test executed against synthetic sandbox payment mock",
        "Network latency does not include multi-region WAN variance",
    ],
    hypotheses=[
        Hypothesis(
            potential_cause="Database write lock contention on inventory or orders table under high concurrency",
            confidence_level="medium",
            rationale="Tail p99 latency degraded disproportionately while average response time remained stable",
            required_evidence_to_confirm="Database query latency telemetry and transaction lock wait time metrics during peak load",
        )
    ],
    sla_assessments=[
        SlaAssessment(
            metric="http_req_duration(p95)",
            target_threshold="< 500 ms",
            actual_value="462.8 ms",
            status=SlaStatus.COMPLIANT,
            details="p95 latency remained within the required 500 ms boundary with a 7.4% safety margin.",
        ),
        SlaAssessment(
            metric="http_req_failed",
            target_threshold="< 1.0%",
            actual_value="0.42%",
            status=SlaStatus.COMPLIANT,
            details="412 failures out of 98,250 requests; well below the 1% error tolerance.",
        ),
    ],
)
