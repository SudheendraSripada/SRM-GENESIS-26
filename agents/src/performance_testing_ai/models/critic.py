from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"

class ValidationCategory(str, Enum):
    TARGET_VALIDITY = "target_validity"
    ENDPOINT_METHOD_VALIDITY = "endpoint_method_validity"
    LOAD_LEVELS = "load_levels"
    DURATION = "duration"
    STAGE_PROGRESSION = "stage_progression"
    THRESHOLDS = "thresholds"
    AUTH_DATA_DEPENDENCIES = "auth_data_dependencies"
    AMBIGUITY = "ambiguity"
    SAFETY_LIMITS = "safety_limits"
    USER_OBJECTIVE_ALIGNMENT = "user_objective_alignment"

class SafetyCheck(BaseModel):
    category: ValidationCategory = Field(..., description="Validation category evaluated")
    status: ValidationStatus = Field(..., description="Outcome: pass, fail, warning")
    description: str = Field(..., description="Description of the safety rule tested")
    details: str = Field(..., description="Findings or rationale")

class CriticResult(BaseModel):
    """
    Contract produced by the Critic/Safety Agent.
    Evaluates safety bounds, configuration sanity, SLA alignment, and provides approval or rejection.
    """
    critic_id: str = Field(..., description="Unique review identifier")
    test_id: str = Field(..., description="Identifier of the evaluated TestSpecification")
    approved: bool = Field(..., description="True if the test is deemed safe and authorized for execution")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Assessed risk level (low, medium, high, critical)")
    issues: List[str] = Field(default_factory=list, description="Critical blocking issues that mandate rejection")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking warnings or observations")
    required_changes: List[str] = Field(default_factory=list, description="Remediations required before test can proceed")
    safety_checks: List[SafetyCheck] = Field(default_factory=list, description="Granular verification checks")
    review_summary: str = Field(..., description="Executive review summary")

    # Backward compatibility properties
    @property
    def is_approved(self) -> bool:
        return self.approved

    @property
    def spec_id(self) -> str:
        return self.test_id

    @property
    def validation_checks(self) -> List[SafetyCheck]:
        return self.safety_checks

    @property
    def summary(self) -> str:
        return self.review_summary

    @property
    def safety_boundary_verified(self) -> bool:
        return self.approved and self.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
