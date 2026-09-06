from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from performance_testing_ai.models.requirement import HttpMethod, TestType, ThresholdSpec
from performance_testing_ai.models.performance_plan import StageSpec

class TargetSystemSpec(BaseModel):
    base_url: str = Field(default="http://staging.local", description="Target base URL")
    default_headers: Dict[str, str] = Field(default_factory=dict, description="Headers applied to all requests")
    timeout_seconds: float = Field(default=30.0, ge=1.0, description="Per-request timeout limit")

class HttpStepSpec(BaseModel):
    name: str = Field(..., description="Step name e.g. 'Submit Checkout'")
    endpoint: str = Field(..., description="API path relative to base_url")
    method: HttpMethod = Field(default=HttpMethod.POST, description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="Step-specific headers")
    payload_schema: Optional[Dict[str, str]] = Field(default=None, description="Declarative payload field descriptions")
    expected_status_codes: List[int] = Field(default_factory=lambda: [200, 201], description="Acceptable HTTP status codes")
    think_time_seconds: float = Field(default=0.5, ge=0.0, description="Pause after this step")

class SafetyConstraintsSpec(BaseModel):
    max_vus: int = Field(..., ge=1, description="Hard upper limit on concurrent users")
    max_duration_seconds: int = Field(..., ge=1, description="Hard upper limit on test duration")
    allowed_domains: List[str] = Field(default_factory=list, description="Permitted target hosts/domains")
    max_rps: Optional[int] = Field(default=None, description="Max rate limit in requests per second")

class TestSpecification(BaseModel):
    """
    Contract produced by the Workload Builder Agent.
    Defines WHAT should be tested declaratively. Does NOT execute code or generate raw runner binaries.
    """
    __test__ = False
    test_id: str = Field(..., description="Unique specification identifier")
    test_name: str = Field(..., description="Human-readable title of the test")
    objective: str = Field(..., description="Explicit performance objective")
    test_type: TestType = Field(..., description="Type of performance test (baseline, load, stress, soak)")
    target: TargetSystemSpec = Field(..., description="Target system configuration")
    load: List[StageSpec] = Field(..., min_length=1, description="Workload stage progression")
    thresholds: List[ThresholdSpec] = Field(default_factory=list, description="Target performance thresholds")
    data_requirements: List[str] = Field(default_factory=list, description="Summary of required datasets")
    authentication_requirements: List[str] = Field(default_factory=list, description="Auth dependencies and schemes")
    request_sequence: List[HttpStepSpec] = Field(default_factory=list, description="Ordered sequence of HTTP interactions")
    success_criteria: List[str] = Field(default_factory=list, description="Conditions for overall test success")
    assumptions: List[str] = Field(default_factory=list, description="Execution assumptions made")
    safety_constraints: SafetyConstraintsSpec = Field(..., description="Enforced safety bounds")

    # Backward compatibility properties
    @property
    def spec_id(self) -> str:
        return self.test_id

    @property
    def title(self) -> str:
        return self.test_name

    @property
    def target_system(self) -> TargetSystemSpec:
        return self.target

    @property
    def workload_schedule(self) -> List[StageSpec]:
        return self.load

    @property
    def scenarios(self) -> List[HttpStepSpec]:
        return self.request_sequence
