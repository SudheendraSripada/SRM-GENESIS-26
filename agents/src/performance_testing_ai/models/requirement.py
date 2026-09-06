from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class TestType(str, Enum):
    __test__ = False
    BASELINE = "baseline"
    LOAD = "load"
    STRESS = "stress"
    SOAK = "soak"

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

class EndpointSpec(BaseModel):
    path: str = Field(..., description="API endpoint path e.g. /api/checkout")
    method: HttpMethod = Field(default=HttpMethod.GET, description="HTTP method")
    is_assumed: bool = Field(default=False, description="Whether this endpoint was assumed rather than explicitly stated")
    description: Optional[str] = Field(default=None, description="Purpose or description of the endpoint")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("Endpoint path must start with '/'")
        return v

class ThresholdSpec(BaseModel):
    metric: str = Field(..., description="Metric name e.g. http_req_duration, http_req_failed")
    aggregation: Optional[str] = Field(default=None, description="Aggregation function like p90, p95, p99, avg, rate")
    operator: str = Field(default="<", description="Comparison operator: <, <=, >, >=")
    value: float = Field(..., description="Threshold numeric value")
    unit: str = Field(default="ms", description="Unit of measurement e.g. ms, %, s")

    @field_validator("value")
    @classmethod
    def validate_positive_value(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Threshold value must be non-negative")
        return v

    @property
    def expression(self) -> str:
        agg = f"({self.aggregation})" if self.aggregation else ""
        return f"{self.metric}{agg} {self.operator} {self.value}{self.unit}"

class RequirementSpec(BaseModel):
    """
    Contract produced by the Requirement Analyst Agent from user natural language input.
    Represents performance testing goals, constraints, assumptions, and missing data.
    Never invents unstated facts or endpoints.
    """
    user_request: str = Field(..., description="Original user prompt or natural language requirement")
    target_application: str = Field(..., description="Name or identifier of the application under test")
    target_base_url: Optional[str] = Field(default=None, description="Base URL of target application if provided")
    endpoints: List[EndpointSpec] = Field(default_factory=list, description="Target endpoints identified or assumed")
    expected_users: int = Field(..., ge=1, description="Target concurrent virtual users (VUs)")
    duration: Optional[str] = Field(default=None, description="Specified test duration e.g. '10m', '1h' (None if unspecified)")
    test_type: TestType = Field(default=TestType.LOAD, description="Inferred or requested test type")
    performance_goals: List[str] = Field(default_factory=list, description="Extracted high-level goals")
    thresholds: List[ThresholdSpec] = Field(default_factory=list, description="Structured quantitative thresholds/SLAs")
    assumptions: List[str] = Field(default_factory=list, description="Explicit assumptions made when information was not stated")
    missing_information: List[str] = Field(default_factory=list, description="Information missing from query needed for execution")

    @property
    def target_endpoints(self) -> List[EndpointSpec]:
        """Backward-compatible alias for endpoints."""
        return self.endpoints
