from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from performance_testing_ai.models.requirement import TestType, ThresholdSpec

class StageSpec(BaseModel):
    duration: str = Field(..., description="Duration string for stage e.g. '2m', '30s'")
    target_vus: int = Field(..., ge=0, description="Target virtual users at the end of this stage")
    description: Optional[str] = Field(default=None, description="Explanation of stage purpose e.g. 'Ramp-up'")

    @field_validator("duration")
    @classmethod
    def validate_duration_format(cls, v: str) -> str:
        if not v or not (v.endswith("s") or v.endswith("m") or v.endswith("h")):
            raise ValueError(f"Duration '{v}' must end in 's', 'm', or 'h'")
        return v

class PerformancePlan(BaseModel):
    """
    Contract produced by the Performance Planner Agent from RequirementSpec.
    Defines the structured execution strategy, stages, concurrency ramp, and success criteria.
    """
    plan_id: str = Field(..., description="Unique identifier for the performance plan")
    test_type: TestType = Field(..., description="Type of performance test to run (baseline, load, stress, soak)")
    objective: str = Field(..., description="High-level engineering objective of the test plan")
    stages: List[StageSpec] = Field(..., min_length=1, description="Ordered execution stages (ramp-up, steady, ramp-down)")
    ramp_up: str = Field(default="2m", description="Duration to ramp up to target concurrency")
    steady_state: str = Field(default="5m", description="Duration to maintain target concurrency")
    ramp_down: str = Field(default="1m", description="Duration to ramp down to zero")
    target_vus: int = Field(..., ge=1, description="Peak concurrent virtual users")
    duration: str = Field(..., description="Total estimated duration across all stages")
    thresholds: List[ThresholdSpec] = Field(default_factory=list, description="Pass/fail SLA thresholds for the plan")
    success_criteria: List[str] = Field(default_factory=list, description="Explicit conditions defining a successful test")
    assumptions: List[str] = Field(default_factory=list, description="Planning assumptions made")

    # Backward compatibility properties
    @property
    def target_concurrency(self) -> int:
        return self.target_vus

    @property
    def ramp_up_duration(self) -> str:
        return self.ramp_up

    @property
    def steady_state_duration(self) -> str:
        return self.steady_state

    @property
    def ramp_down_duration(self) -> str:
        return self.ramp_down
