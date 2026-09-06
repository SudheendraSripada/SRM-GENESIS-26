from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from performance_testing_ai.models.execution_result import ThresholdResult

class SlaStatus(str, Enum):
    COMPLIANT = "compliant"
    VIOLATED = "violated"
    AT_RISK = "at_risk"

class SlaAssessment(BaseModel):
    metric: str = Field(..., description="Name of the evaluated SLA metric")
    target_threshold: str = Field(..., description="Target threshold defined in requirements")
    actual_value: str = Field(..., description="Actual value measured in execution")
    status: SlaStatus = Field(..., description="SLA evaluation outcome")
    details: str = Field(..., description="Explanation of compliance or violation extent")

class Observation(BaseModel):
    """
    Factual, empirical measurement observed directly from test execution data.
    Must NOT contain unproven assumptions, root-cause speculation, or opinions.
    """
    metric_or_signal: str = Field(..., description="Observed metric e.g. p95 latency, error count")
    observed_fact: str = Field(..., description="Empirical fact directly backed by data")
    evidence_source: str = Field(..., description="Exact field or log reference supporting this fact")

class Hypothesis(BaseModel):
    """
    A potential cause explaining one or more observations.
    Must be explicitly designated as a hypothesis until verified with concrete instrumentation evidence.
    """
    potential_cause: str = Field(..., description="Hypothesized explanation for observed performance behavior")
    confidence_level: str = Field(default="medium", description="Confidence level: low, medium, high")
    rationale: str = Field(..., description="Reasoning connecting observations to this hypothesis")
    required_evidence_to_confirm: str = Field(..., description="Concrete telemetry or profiling required to prove root cause")

class BottleneckIndicator(BaseModel):
    suspected_component: str = Field(..., description="Component exhibiting degradation e.g. DB connection pool, CPU, Network")
    evidence: str = Field(..., description="Empirical indicators pointing to this bottleneck")
    severity: str = Field(default="major", description="Bottleneck severity: minor, major, critical")

class AnalysisResult(BaseModel):
    """
    Contract produced by the Performance Analyst Agent from ExecutionResult.
    Rigidly separates empirical observations from hypotheses and avoids unevidenced root-cause claims.
    """
    analysis_id: str = Field(..., description="Unique analysis report ID")
    test_id: str = Field(..., description="Associated test specification / run ID")
    overall_status: str = Field(..., description="Status string e.g. 'PASSED', 'FAILED', 'DEGRADED'")
    observations: List[Observation] = Field(default_factory=list, description="Strict empirical measurements observed in data")
    threshold_results: List[ThresholdResult] = Field(default_factory=list, description="Direct evaluations of threshold criteria")
    performance_findings: List[str] = Field(default_factory=list, description="High-level performance diagnostic findings")
    possible_bottlenecks: List[BottleneckIndicator] = Field(default_factory=list, description="Identified performance bottlenecks")
    degradation_point: Optional[str] = Field(default=None, description="Concurrency or throughput level where degradation began")
    recommendations: List[str] = Field(default_factory=list, description="Actionable engineering recommendations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score in the analysis findings (0.0 to 1.0)")
    limitations: List[str] = Field(default_factory=list, description="Known analytical caveats or data limitations")

    # Additional analytical details
    hypotheses: List[Hypothesis] = Field(default_factory=list, description="Hypotheses requiring instrumentation to confirm")
    sla_assessments: List[SlaAssessment] = Field(default_factory=list, description="SLA assessments")

    # Backward compatibility properties
    @property
    def overall_sla_met(self) -> bool:
        return self.overall_status.upper() in ("PASSED", "COMPLIANT", "SUCCESS")

    @property
    def execution_id(self) -> str:
        return self.test_id

    @property
    def executive_summary(self) -> str:
        return " | ".join(self.performance_findings) if self.performance_findings else f"Test {self.overall_status}"

    @property
    def actionable_recommendations(self) -> List[str]:
        return self.recommendations
