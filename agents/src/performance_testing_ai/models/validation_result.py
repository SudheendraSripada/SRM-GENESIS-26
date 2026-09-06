from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationErrorCode(str, Enum):
    # Basic specification validity
    INVALID_BASIC_SPECIFICATION = "INVALID_BASIC_SPECIFICATION"
    # Target URL
    INVALID_TARGET_URL = "INVALID_TARGET_URL"
    # Domain authorization
    UNAUTHORIZED_TARGET_DOMAIN = "UNAUTHORIZED_TARGET_DOMAIN"
    ALLOWED_DOMAINS_EMPTY = "ALLOWED_DOMAINS_EMPTY"
    # Load / VU
    LOAD_TARGET_EXCEEDS_MAX_VUS = "LOAD_TARGET_EXCEEDS_MAX_VUS"
    EMPTY_WORKLOAD_STAGES = "EMPTY_WORKLOAD_STAGES"
    # Stage & Duration
    INVALID_STAGE_DURATION = "INVALID_STAGE_DURATION"
    DURATION_EXCEEDS_SAFETY_LIMIT = "DURATION_EXCEEDS_SAFETY_LIMIT"
    # Request sequence
    EMPTY_REQUEST_SEQUENCE = "EMPTY_REQUEST_SEQUENCE"
    INVALID_REQUEST_PATH = "INVALID_REQUEST_PATH"
    UNSUPPORTED_HTTP_METHOD = "UNSUPPORTED_HTTP_METHOD"
    REQUEST_TIMEOUT_EXCEEDS_LIMIT = "REQUEST_TIMEOUT_EXCEEDS_LIMIT"
    # Thresholds
    INVALID_THRESHOLD = "INVALID_THRESHOLD"
    # Cross-field consistency
    CROSS_FIELD_INCONSISTENCY = "CROSS_FIELD_INCONSISTENCY"
    # Upstream Critic Gate
    CRITIC_GATE_REJECTED = "CRITIC_GATE_REJECTED"
    NO_CRITIC_RESULT = "NO_CRITIC_RESULT"

class ValidationIssue(BaseModel):
    code: str = Field(..., description="Stable machine-readable error or warning code")
    severity: ValidationSeverity = Field(..., description="Issue severity: error, warning, or info")
    field: str = Field(..., description="Field path identifying where the issue occurred e.g. 'target.base_url'")
    message: str = Field(..., description="Human-readable explanation of the validation issue")

class ValidationResult(BaseModel):
    """
    Contract produced by the Deterministic TestSpecification Validator (Phase 3A).
    Represents whether a TestSpecification is safe, consistent, and ready for future k6 compilation.
    """
    valid: bool = Field(..., description="True if zero validation errors were encountered")
    errors: List[ValidationIssue] = Field(default_factory=list, description="List of blocking validation errors")
    warnings: List[ValidationIssue] = Field(default_factory=list, description="List of non-blocking warnings")
    checks_performed: int = Field(default=0, ge=0, description="Total number of verification checks executed")
    checks_passed: int = Field(default=0, ge=0, description="Number of verification checks that passed without errors")
    summary: str = Field(..., description="Executive summary of the validation outcome")

    @property
    def error_codes(self) -> List[str]:
        """Convenience property returning unique error codes."""
        return [e.code for e in self.errors]

    @property
    def warning_codes(self) -> List[str]:
        """Convenience property returning unique warning codes."""
        return [w.code for w in self.warnings]
