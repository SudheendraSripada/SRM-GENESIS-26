import re
from typing import List, Optional
from urllib.parse import urlparse

from performance_testing_ai.models.requirement import HttpMethod
from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.critic import CriticResult
from performance_testing_ai.models.validation_result import (
    ValidationSeverity,
    ValidationErrorCode,
    ValidationIssue,
    ValidationResult,
)

# Deterministic duration regex: positive integer ending in s, m, or h
DURATION_REGEX = re.compile(r"^([1-9]\d*)([smh])$")

def parse_duration_seconds(duration: str) -> int:
    """
    Deterministically parses a duration string into total integer seconds.
    Supported units: 's' (seconds), 'm' (minutes), 'h' (hours).
    Only strictly positive integer durations are permitted (e.g. '10s', '2m', '1h').
    
    Raises:
        ValueError: If duration format is invalid, zero, or negative.
    """
    if not duration or not isinstance(duration, str):
        raise ValueError(f"Duration must be a non-empty string, got {type(duration).__name__}")

    duration_clean = duration.strip()
    match = DURATION_REGEX.match(duration_clean)
    if not match:
        raise ValueError(
            f"Invalid duration format: '{duration}'. "
            "Must be a positive non-zero integer followed by 's', 'm', or 'h' (e.g., '10s', '2m', '1h')."
        )

    val_str, unit = match.groups()
    val = int(val_str)

    if unit == "s":
        return val
    elif unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    else:
        raise ValueError(f"Unsupported duration unit: '{unit}'")

def _validate_basic_specification(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """A. Validates basic identification and essential structures."""
    if not spec.test_id or not spec.test_id.strip():
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_BASIC_SPECIFICATION.value,
            severity=ValidationSeverity.ERROR,
            field="test_id",
            message="Test specification test_id must be a non-empty string.",
        ))

    if not spec.test_name or not spec.test_name.strip():
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_BASIC_SPECIFICATION.value,
            severity=ValidationSeverity.ERROR,
            field="test_name",
            message="Test specification test_name must be a non-empty string.",
        ))

    if not spec.objective or not spec.objective.strip():
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_BASIC_SPECIFICATION.value,
            severity=ValidationSeverity.ERROR,
            field="objective",
            message="Test specification objective must be a non-empty string.",
        ))

def _validate_target_url(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """B. Validates target system base URL format and scheme."""
    base_url = spec.target.base_url
    if not base_url or not isinstance(base_url, str):
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_TARGET_URL.value,
            severity=ValidationSeverity.ERROR,
            field="target.base_url",
            message="Target base_url must be a non-empty string.",
        ))
        return

    if " " in base_url:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_TARGET_URL.value,
            severity=ValidationSeverity.ERROR,
            field="target.base_url",
            message=f"Target base_url '{base_url}' contains invalid whitespace.",
        ))
        return

    parsed = urlparse(base_url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_TARGET_URL.value,
            severity=ValidationSeverity.ERROR,
            field="target.base_url",
            message=f"Target base_url '{base_url}' must use an absolute 'http' or 'https' scheme (got '{scheme}').",
        ))
        return

    if not parsed.netloc or not parsed.hostname:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.INVALID_TARGET_URL.value,
            severity=ValidationSeverity.ERROR,
            field="target.base_url",
            message=f"Target base_url '{base_url}' does not contain a valid hostname.",
        ))

def _validate_allowed_domains(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """C. Validates that target hostname strictly matches allowed_domains whitelist."""
    allowed_domains = spec.safety_constraints.allowed_domains
    if not allowed_domains:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.ALLOWED_DOMAINS_EMPTY.value,
            severity=ValidationSeverity.ERROR,
            field="safety_constraints.allowed_domains",
            message="Allowed domains whitelist is empty. At least one authorized domain must be explicitly configured.",
        ))
        return

    parsed = urlparse(spec.target.base_url)
    target_host = (parsed.hostname or "").lower()
    if not target_host:
        # Already reported in _validate_target_url
        return

    is_authorized = False
    for allowed in allowed_domains:
        clean_allowed = allowed.lower().strip()
        if clean_allowed.startswith("*."):
            clean_allowed = clean_allowed[2:]
        elif clean_allowed.startswith("."):
            clean_allowed = clean_allowed[1:]

        # Exact match (e.g. localhost, 127.0.0.1, staging-ecom.local)
        if target_host == clean_allowed:
            is_authorized = True
            break

        # Safe subdomain match (e.g. api.staging-ecom.local -> staging-ecom.local)
        # Prevents spoofing: example.com.evil.com will NOT match example.com
        # evil-example.com will NOT match example.com
        if target_host.endswith("." + clean_allowed):
            is_authorized = True
            break

    if not is_authorized:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.UNAUTHORIZED_TARGET_DOMAIN.value,
            severity=ValidationSeverity.ERROR,
            field="target.base_url",
            message=(
                f"Target hostname '{target_host}' is unauthorized. "
                f"Must match an allowed domain in {allowed_domains}."
            ),
        ))

def _validate_load_and_vus(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """D. Validates load levels, concurrency caps, and stage consistency."""
    max_vus = spec.safety_constraints.max_vus
    if max_vus <= 0:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.LOAD_TARGET_EXCEEDS_MAX_VUS.value,
            severity=ValidationSeverity.ERROR,
            field="safety_constraints.max_vus",
            message=f"Safety max_vus must be greater than zero, got {max_vus}.",
        ))

    if not spec.load:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.EMPTY_WORKLOAD_STAGES.value,
            severity=ValidationSeverity.ERROR,
            field="load",
            message="Workload schedule contains no stages. At least one stage is required.",
        ))
        return

    for idx, stage in enumerate(spec.load):
        if stage.target_vus < 0:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.LOAD_TARGET_EXCEEDS_MAX_VUS.value,
                severity=ValidationSeverity.ERROR,
                field=f"load[{idx}].target_vus",
                message=f"Stage {idx} target_vus cannot be negative: {stage.target_vus}.",
            ))
        elif stage.target_vus > max_vus:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.LOAD_TARGET_EXCEEDS_MAX_VUS.value,
                severity=ValidationSeverity.ERROR,
                field=f"load[{idx}].target_vus",
                message=(
                    f"Stage {idx} target VUs ({stage.target_vus}) exceeds "
                    f"safety limit max_vus ({max_vus})."
                ),
            ))

def _validate_stages_and_duration(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """E & F. Validates stage duration formats and total duration boundary."""
    total_seconds = 0
    duration_errors = False

    for idx, stage in enumerate(spec.load):
        try:
            sec = parse_duration_seconds(stage.duration)
            total_seconds += sec
        except ValueError as exc:
            duration_errors = True
            errors.append(ValidationIssue(
                code=ValidationErrorCode.INVALID_STAGE_DURATION.value,
                severity=ValidationSeverity.ERROR,
                field=f"load[{idx}].duration",
                message=f"Stage {idx} duration '{stage.duration}' is invalid: {str(exc)}",
            ))

    max_duration = spec.safety_constraints.max_duration_seconds
    if max_duration <= 0:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.DURATION_EXCEEDS_SAFETY_LIMIT.value,
            severity=ValidationSeverity.ERROR,
            field="safety_constraints.max_duration_seconds",
            message=f"Safety max_duration_seconds must be > 0, got {max_duration}.",
        ))
        return

    if not duration_errors:
        if total_seconds > max_duration:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.DURATION_EXCEEDS_SAFETY_LIMIT.value,
                severity=ValidationSeverity.ERROR,
                field="load",
                message=(
                    f"Total workload duration ({total_seconds}s) exceeds "
                    f"safety limit max_duration_seconds ({max_duration}s)."
                ),
            ))

def _validate_request_sequence(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """G & H. Validates HTTP request sequence, paths, methods, and step timeouts."""
    if not spec.request_sequence:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.EMPTY_REQUEST_SEQUENCE.value,
            severity=ValidationSeverity.ERROR,
            field="request_sequence",
            message="Request sequence is empty. Test specification must contain at least one HTTP step.",
        ))
        return

    valid_http_methods = {m.value for m in HttpMethod}

    for idx, step in enumerate(spec.request_sequence):
        # Step name
        if not step.name or not step.name.strip():
            warnings.append(ValidationIssue(
                code="UNNAMED_HTTP_STEP",
                severity=ValidationSeverity.WARNING,
                field=f"request_sequence[{idx}].name",
                message=f"Step {idx} has an empty or uninformative name.",
            ))

        # Endpoint path
        endpoint = step.endpoint
        if not endpoint or not endpoint.startswith("/"):
            errors.append(ValidationIssue(
                code=ValidationErrorCode.INVALID_REQUEST_PATH.value,
                severity=ValidationSeverity.ERROR,
                field=f"request_sequence[{idx}].endpoint",
                message=f"Step {idx} ('{step.name}') endpoint must start with '/', got '{endpoint}'.",
            ))
        elif " " in endpoint:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.INVALID_REQUEST_PATH.value,
                severity=ValidationSeverity.ERROR,
                field=f"request_sequence[{idx}].endpoint",
                message=f"Step {idx} ('{step.name}') endpoint contains invalid whitespace: '{endpoint}'.",
            ))

        # HTTP Method
        method_str = step.method.value if isinstance(step.method, HttpMethod) else str(step.method)
        if method_str not in valid_http_methods:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.UNSUPPORTED_HTTP_METHOD.value,
                severity=ValidationSeverity.ERROR,
                field=f"request_sequence[{idx}].method",
                message=(
                    f"Step {idx} ('{step.name}') uses unsupported HTTP method '{method_str}'. "
                    f"Supported methods: {sorted(list(valid_http_methods))}."
                ),
            ))

        # Think time
        if step.think_time_seconds < 0:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.CROSS_FIELD_INCONSISTENCY.value,
                severity=ValidationSeverity.ERROR,
                field=f"request_sequence[{idx}].think_time_seconds",
                message=f"Step {idx} think_time_seconds cannot be negative, got {step.think_time_seconds}.",
            ))

    # Request timeout check against max duration
    timeout = spec.target.timeout_seconds
    max_duration = spec.safety_constraints.max_duration_seconds
    if timeout > max_duration:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.REQUEST_TIMEOUT_EXCEEDS_LIMIT.value,
            severity=ValidationSeverity.ERROR,
            field="target.timeout_seconds",
            message=(
                f"Per-request timeout ({timeout}s) exceeds total test duration limit ({max_duration}s)."
            ),
        ))

def _validate_thresholds(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """I. Validates SLA threshold specifications."""
    if not spec.thresholds:
        warnings.append(ValidationIssue(
            code="MISSING_THRESHOLDS",
            severity=ValidationSeverity.WARNING,
            field="thresholds",
            message="No quantitative thresholds defined; SLA verification will be unmeasurable.",
        ))
        return

    for idx, t in enumerate(spec.thresholds):
        if t.value < 0:
            errors.append(ValidationIssue(
                code=ValidationErrorCode.INVALID_THRESHOLD.value,
                severity=ValidationSeverity.ERROR,
                field=f"thresholds[{idx}].value",
                message=f"Threshold '{t.metric}' value must be non-negative, got {t.value}.",
            ))

        metric_lower = t.metric.lower()
        if "failed" in metric_lower or "error" in metric_lower:
            if t.unit == "%" and t.value > 100.0:
                errors.append(ValidationIssue(
                    code=ValidationErrorCode.INVALID_THRESHOLD.value,
                    severity=ValidationSeverity.ERROR,
                    field=f"thresholds[{idx}].value",
                    message=f"Error rate threshold percentage cannot exceed 100%, got {t.value}%.",
                ))
            elif t.unit in ("", "rate") and t.value > 1.0:
                errors.append(ValidationIssue(
                    code=ValidationErrorCode.INVALID_THRESHOLD.value,
                    severity=ValidationSeverity.ERROR,
                    field=f"thresholds[{idx}].value",
                    message=f"Error rate threshold fraction cannot exceed 1.0, got {t.value}.",
                ))

def _validate_cross_field_consistency(
    spec: TestSpecification,
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """J. Validates cross-field relationships and consistency."""
    # Ensure peak VU across stages is > 0 if request sequence exists
    if spec.load and spec.request_sequence:
        peak_vus = max((s.target_vus for s in spec.load), default=0)
        if peak_vus == 0:
            warnings.append(ValidationIssue(
                code="ZERO_PEAK_VUS",
                severity=ValidationSeverity.WARNING,
                field="load",
                message="Workload schedule peak VUs is 0; test will execute no simulated load.",
            ))

def _validate_critic_gate(
    spec: TestSpecification,
    critic_result: Optional[CriticResult],
    errors: List[ValidationIssue],
    warnings: List[ValidationIssue],
) -> None:
    """K. Validates upstream Critic approval."""
    if critic_result is None:
        warnings.append(ValidationIssue(
            code=ValidationErrorCode.NO_CRITIC_RESULT.value,
            severity=ValidationSeverity.INFO,
            field="critic_result",
            message=(
                "No CriticResult was provided. Standalone validation evaluated specification rules "
                "without upstream critic review."
            ),
        ))
        return

    if not critic_result.approved:
        errors.append(ValidationIssue(
            code=ValidationErrorCode.CRITIC_GATE_REJECTED.value,
            severity=ValidationSeverity.ERROR,
            field="critic_result.approved",
            message=f"Upstream safety Critic gate rejected the specification: {critic_result.review_summary}",
        ))

    if critic_result.test_id != spec.test_id:
        warnings.append(ValidationIssue(
            code="CRITIC_TEST_ID_MISMATCH",
            severity=ValidationSeverity.WARNING,
            field="critic_result.test_id",
            message=(
                f"Critic test_id '{critic_result.test_id}' does not match "
                f"specification test_id '{spec.test_id}'."
            ),
        ))

def validate_test_specification(
    spec: TestSpecification,
    critic_result: Optional[CriticResult] = None,
) -> ValidationResult:
    """
    Deterministic TestSpecification Validator (Phase 3A).
    
    Verifies that a TestSpecification is safe, internally consistent, complete,
    and valid for future k6 script compilation.
    
    Guarantees:
    - 100% deterministic (same input produces identical output).
    - Read-only: never mutates input specification or critic result.
    - Zero external network requests, shell execution, k6 calls, or LLM invocations.
    - Captures multiple errors rather than failing on the first error.
    
    Args:
        spec: The TestSpecification to validate.
        critic_result: Optional CriticResult from upstream safety agent.
        
    Returns:
        ValidationResult with validation status, error/warning issues, and summary.
    """
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    # Category checks in predictable order
    checks = [
        ("Basic Specification Validity", lambda: _validate_basic_specification(spec, errors, warnings)),
        ("Target URL Validation", lambda: _validate_target_url(spec, errors, warnings)),
        ("Authorized Domains Validation", lambda: _validate_allowed_domains(spec, errors, warnings)),
        ("Load and VU Caps Validation", lambda: _validate_load_and_vus(spec, errors, warnings)),
        ("Stage Durations & Boundary Validation", lambda: _validate_stages_and_duration(spec, errors, warnings)),
        ("Request Sequence & Method Validation", lambda: _validate_request_sequence(spec, errors, warnings)),
        ("SLA Thresholds Validation", lambda: _validate_thresholds(spec, errors, warnings)),
        ("Cross-Field Consistency Validation", lambda: _validate_cross_field_consistency(spec, errors, warnings)),
        ("Upstream Critic Gate Validation", lambda: _validate_critic_gate(spec, critic_result, errors, warnings)),
    ]

    checks_performed = len(checks)
    checks_passed = 0

    for name, check_fn in checks:
        initial_error_count = len(errors)
        check_fn()
        if len(errors) == initial_error_count:
            checks_passed += 1

    valid = len(errors) == 0

    if valid:
        if warnings:
            summary = (
                f"VALID WITH WARNINGS: Specification passed validation ({checks_passed}/{checks_performed} check suites) "
                f"with {len(warnings)} non-blocking warning(s)."
            )
        else:
            summary = (
                f"VALID: Specification passed all {checks_performed} deterministic validation check suites successfully."
            )
    else:
        summary = (
            f"INVALID: Specification failed validation with {len(errors)} blocking error(s) "
            f"across {checks_performed - checks_passed} check suite(s)."
        )

    return ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        checks_performed=checks_performed,
        checks_passed=checks_passed,
        summary=summary,
    )
