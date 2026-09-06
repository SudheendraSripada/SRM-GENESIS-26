from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StageName(str, Enum):
    SYNTAX = "syntax"
    SCHEMA = "schema"
    CONSTRAINTS = "constraints"
    SEMANTIC = "semantic"
    CROSS_FIELD = "cross_field"
    SAFETY = "safety"
    K6_COMPATIBILITY = "k6_compatibility"
    NORMALIZATION = "normalization"
    COMPILATION = "compilation"


class StageStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


class PipelineStatus(str, Enum):
    VALID = "VALID"
    REJECTED = "REJECTED"
    WARNING = "WARNING"


class ValidationErrorItem(BaseModel):
    code: str = Field(..., description="Unique machine-readable error code, e.g., SYNTAX_001")
    stage: StageName = Field(..., description="Validation stage where violation was detected")
    path: str = Field(..., description="Dot-separated path or JSONPath to invalid node")
    message: str = Field(..., description="Human-readable explanation of error")
    severity: Severity = Field(default=Severity.ERROR)
    expected: Optional[str] = Field(default=None, description="Expected value, type, or constraint")
    received: Optional[str] = Field(default=None, description="Actual received value or representation")
    repair_hint: Optional[str] = Field(default=None, description="Actionable hint for agent self-healing")


class ValidationResult(BaseModel):
    status: PipelineStatus = Field(..., description="Authoritative verdict: VALID or REJECTED")
    spec_version: str = Field(default="1.0")
    validation_score: int = Field(default=100, ge=0, le=100, description="UX score from 0 to 100")
    stages: Dict[str, StageStatus] = Field(default_factory=dict, description="Status for each stage")
    errors: List[ValidationErrorItem] = Field(default_factory=list, description="Fatal errors rejecting spec")
    warnings: List[ValidationErrorItem] = Field(default_factory=list, description="Non-blocking recommendations")
    normalized_spec: Optional[Dict[str, Any]] = Field(default=None, description="Canonical Spec IR")
    compiled_k6_script: Optional[str] = Field(default=None, description="Executable k6 ES6 script")


# Central Error Code Catalog
class ErrorCatalog:
    # Syntax (100-199)
    SYNTAX_INVALID_JSON = "SYNTAX_001"
    SYNTAX_MARKDOWN_BLOCK = "SYNTAX_002"
    SYNTAX_EMPTY_PAYLOAD = "SYNTAX_003"
    SYNTAX_UNCLOSED_BRACE = "SYNTAX_004"

    # Schema (200-299)
    SCHEMA_MISSING_FIELD = "SCHEMA_001"
    SCHEMA_INVALID_TYPE = "SCHEMA_002"
    SCHEMA_UNRECOGNIZED_FIELD = "SCHEMA_003"

    # Primitive Constraints (300-399)
    CONSTRAINT_INVALID_METHOD = "CONSTRAINT_001"
    CONSTRAINT_VUS_RANGE = "CONSTRAINT_002"
    CONSTRAINT_DURATION_RANGE = "CONSTRAINT_003"
    CONSTRAINT_INVALID_URL = "CONSTRAINT_004"
    CONSTRAINT_INVALID_STAGE = "CONSTRAINT_005"
    CONSTRAINT_INVALID_PROTOCOL = "CONSTRAINT_006"

    # Semantic Profile (400-499)
    SEMANTIC_INVALID_TEST_TYPE = "SEMANTIC_001"
    SEMANTIC_STRESS_NON_INCREASING = "SEMANTIC_002"
    SEMANTIC_SOAK_TOO_SHORT = "SEMANTIC_003"
    SEMANTIC_SPIKE_INSUFFICIENT_PEAK = "SEMANTIC_004"
    SEMANTIC_BASELINE_UNSTABLE = "SEMANTIC_005"

    # Cross-Field & Dependency (500-599)
    CROSS_FIELD_DURATION_MISMATCH = "CROSS_001"
    CROSS_FIELD_GET_WITH_BODY = "CROSS_002"
    CROSS_FIELD_CONTENT_TYPE_MISMATCH = "CROSS_003"
    CROSS_FIELD_UNRESOLVED_VARIABLE = "CROSS_004"
    CROSS_FIELD_MALFORMED_VARIABLE_TOKEN = "CROSS_005"
    CROSS_FIELD_START_GREATER_THAN_TARGET = "CROSS_006"

    # Safety & Security (600-699)
    SAFETY_MAX_VUS_EXCEEDED = "SAFETY_001"
    SAFETY_MAX_DURATION_EXCEEDED = "SAFETY_002"
    SAFETY_MAX_STAGES_EXCEEDED = "SAFETY_003"
    SAFETY_TARGET_NOT_ALLOWED = "SAFETY_004"
    SAFETY_SSRF_PROHIBITED_IP = "SAFETY_005"
    SAFETY_DESTRUCTIVE_METHOD_PROHIBITED = "SAFETY_006"

    # k6 Compatibility (700-799)
    K6_UNSUPPORTED_EXECUTOR = "K6_001"
    K6_INVALID_THRESHOLD_METRIC = "K6_002"
    K6_INVALID_THRESHOLD_SYNTAX = "K6_003"
    K6_UNSUPPORTED_AUTH_TYPE = "K6_004"
    K6_UNSUPPORTED_PROTOCOL = "K6_005"
