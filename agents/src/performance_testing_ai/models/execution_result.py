from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"
    TIMED_OUT = "timed_out"

class ExecutionMetrics(BaseModel):
    requests: int = Field(..., ge=0, description="Total HTTP requests processed")
    rps: float = Field(..., ge=0.0, description="Average requests per second")
    avg_latency_ms: float = Field(..., ge=0.0, description="Mean response time in milliseconds")
    p95_ms: float = Field(..., ge=0.0, description="95th percentile latency in milliseconds")
    p99_ms: float = Field(..., ge=0.0, description="99th percentile latency in milliseconds")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Fraction of failed requests (0.0 to 1.0)")
    iterations: int = Field(..., ge=0, description="Total completed virtual user iterations")

class StageMetric(BaseModel):
    stage_index: int = Field(..., ge=0, description="Zero-based stage index")
    vus: int = Field(..., ge=0, description="VUs active during this stage")
    avg_duration_ms: float = Field(..., ge=0.0, description="Average response time during this stage")
    error_rate: float = Field(..., ge=0.0, le=1.0, description="Error rate during this stage")

class ThresholdResult(BaseModel):
    metric: str = Field(..., description="Metric evaluated")
    threshold_expression: str = Field(..., description="Target expression e.g. 'p95 < 500ms'")
    actual_value: float = Field(..., description="Observed numeric value")
    passed: bool = Field(..., description="Whether the threshold was met")

class ExecutionResult(BaseModel):
    """
    Contract representing the output of the future test execution engine (e.g. k6 runner).
    Consumed by the Performance Analyst Agent.
    """
    test_id: str = Field(..., description="Associated TestSpecification identifier")
    status: ExecutionStatus = Field(..., description="Overall execution status")
    start_time: Optional[str] = Field(default=None, description="Execution start timestamp (ISO-8601)")
    end_time: Optional[str] = Field(default=None, description="Execution end timestamp (ISO-8601)")
    metrics: ExecutionMetrics = Field(..., description="Core performance metrics summary")
    thresholds: List[ThresholdResult] = Field(default_factory=list, description="Evaluations of defined thresholds")
    errors: List[str] = Field(default_factory=list, description="List of error messages or failure descriptions")
    raw_summary_reference: Optional[str] = Field(default=None, description="URI or path to the raw execution report/JSON")

    # Backward compatibility properties
    @property
    def total_requests(self) -> int:
        return self.metrics.requests

    @property
    def error_rate(self) -> float:
        return self.metrics.error_rate

    @property
    def throughput_rps(self) -> float:
        return self.metrics.rps

    @property
    def http_req_duration(self):
        class _Duration:
            p95_ms = self.metrics.p95_ms
            p99_ms = self.metrics.p99_ms
            avg_ms = self.metrics.avg_latency_ms
        return _Duration()

    @property
    def threshold_results(self) -> List[ThresholdResult]:
        return self.thresholds

    @property
    def spec_id(self) -> str:
        return self.test_id

    @property
    def execution_id(self) -> str:
        return self.test_id
