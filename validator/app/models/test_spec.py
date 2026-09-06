from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class Metadata(BaseModel):
    test_id: Optional[str] = Field(default=None, description="Unique identifier for the test run")
    name: str = Field(default="k6 Performance Test", description="Human-readable title of the test")
    description: Optional[str] = Field(default=None, description="Detailed test scenario description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metadata tags for filtering and analytics")


class TestTypeConfig(BaseModel):
    type: str = Field(default="load", description="Test category: baseline, load, stress, spike, soak")
    protocol: str = Field(default="http", description="Application protocol: http, https, websocket, grpc")


class TargetConfig(BaseModel):
    base_url: str = Field(..., description="Target server base URL, e.g. https://staging.internal.net")
    endpoint: str = Field(default="/", description="Relative path endpoint, e.g. /api/v1/login")
    method: str = Field(default="GET", description="HTTP Method: GET, POST, PUT, PATCH, DELETE, etc.")
    timeout_ms: int = Field(default=10000, description="Request timeout in milliseconds")


class StageConfig(BaseModel):
    duration_seconds: int = Field(..., description="Duration of this stage ramp/plateau in seconds")
    target_vus: int = Field(..., description="Target virtual users at the end of this stage")


class LoadConfig(BaseModel):
    strategy: str = Field(default="stages", description="Execution strategy: stages, constant, arrival_rate")
    start_vus: int = Field(default=1, description="Initial virtual users")
    target_vus: int = Field(default=10, description="Peak or steady-state virtual users")
    duration_seconds: int = Field(default=60, description="Total planned test duration in seconds")


class PayloadConfig(BaseModel):
    type: str = Field(default="json", description="Payload serialization: json, form, raw, none")
    body: Optional[Any] = Field(default=None, description="Payload data (dict, list, or string)")


class AuthConfig(BaseModel):
    type: str = Field(default="none", description="Authentication mechanism: none, bearer, basic")
    token: Optional[str] = Field(default=None, description="Bearer token or template {{token}}")
    username: Optional[str] = Field(default=None, description="Basic auth username")
    password: Optional[str] = Field(default=None, description="Basic auth password")


class ThresholdRule(BaseModel):
    metric: str = Field(..., description="Metric identifier, e.g. http_req_duration, http_req_failed")
    percentile: Optional[int] = Field(default=None, description="Percentile 1-100 (e.g. 95 for p95)")
    aggregation: Optional[str] = Field(default=None, description="Aggregation function: rate, avg, min, max, count")
    operator: str = Field(default="<", description="Comparison operator: <, <=, >, >=, ==")
    value: Union[float, int] = Field(..., description="Threshold numeric cutoff value")


class CheckRule(BaseModel):
    name: str = Field(..., description="Assertion title, e.g. 'status is 200'")
    expression: str = Field(..., description="k6 JavaScript boolean check expression")


class TestSpec(BaseModel):
    __test__ = False
    version: str = Field(default="1.0", description="Contract version")
    metadata: Metadata = Field(default_factory=Metadata)
    test: TestTypeConfig = Field(default_factory=TestTypeConfig)
    target: TargetConfig = Field(...)
    load: LoadConfig = Field(...)
    stages: List[StageConfig] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    payload: PayloadConfig = Field(default_factory=PayloadConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    thresholds: Union[List[ThresholdRule], Dict[str, Any]] = Field(default_factory=list)
    checks: List[CheckRule] = Field(default_factory=list)
