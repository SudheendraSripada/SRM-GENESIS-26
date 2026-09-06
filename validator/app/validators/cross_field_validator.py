import re
import json
from typing import List, Tuple, Set, Any
from app.models.test_spec import TestSpec
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class CrossFieldValidator:
    """
    Stage 5: Cross-Field Invariant & Dependency Validator.
    - Conservation of stage duration: sum(stage.duration) == load.duration.
    - Method-vs-Payload consistency (GET/HEAD with non-empty body).
    - Content-Type and payload.type agreement.
    - Variable syntax inspection (e.g. unclosed {{var).
    - start_vus vs target_vus logical relationship.
    """

    _TEMPLATE_VAR_RE = re.compile(r"\{\{([a-zA-Z0-9_\-]+)\}\}")
    _MALFORMED_VAR_RE = re.compile(r"\{\{[a-zA-Z0-9_\-]+(?!\}\})")

    @classmethod
    def validate(cls, spec: TestSpec) -> Tuple[List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        # 1. Conservation of duration if stages provided
        if spec.stages:
            stage_duration_sum = sum(s.duration_seconds for s in spec.stages)
            if stage_duration_sum != spec.load.duration_seconds:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CROSS_FIELD_DURATION_MISMATCH,
                        stage=StageName.CROSS_FIELD,
                        path="load.duration_seconds",
                        message=(
                            f"Sum of stage durations ({stage_duration_sum}s) does not match "
                            f"load.duration_seconds ({spec.load.duration_seconds}s)"
                        ),
                        severity=Severity.ERROR,
                        expected=f"{stage_duration_sum} seconds",
                        received=f"{spec.load.duration_seconds} seconds",
                        repair_hint=(
                            f"Set 'load.duration_seconds' to {stage_duration_sum} "
                            f"or adjust stage durations to sum to {spec.load.duration_seconds}."
                        )
                    )
                )

        # 2. start_vus vs target_vus check (RULE-001)
        if spec.load.start_vus > spec.load.target_vus and not spec.stages:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CROSS_FIELD_START_GREATER_THAN_TARGET,
                    stage=StageName.CROSS_FIELD,
                    path="load.start_vus",
                    message=f"start_vus ({spec.load.start_vus}) cannot be greater than target_vus ({spec.load.target_vus})",
                    severity=Severity.ERROR,
                    expected=f"<= {spec.load.target_vus}",
                    received=str(spec.load.start_vus),
                    repair_hint="Set start_vus <= target_vus."
                )
            )

        # 3. Method vs Payload body consistency
        method_upper = spec.target.method.upper()
        if method_upper in ("GET", "HEAD") and spec.payload.body:
            is_non_empty = False
            if isinstance(spec.payload.body, dict) and len(spec.payload.body) > 0:
                is_non_empty = True
            elif isinstance(spec.payload.body, str) and spec.payload.body.strip():
                is_non_empty = True
            elif isinstance(spec.payload.body, (list, tuple)) and len(spec.payload.body) > 0:
                is_non_empty = True

            if is_non_empty:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CROSS_FIELD_GET_WITH_BODY,
                        stage=StageName.CROSS_FIELD,
                        path="payload.body",
                        message=f"HTTP {method_upper} requests should not have a request body",
                        severity=Severity.ERROR,
                        expected="Empty payload body for GET/HEAD",
                        received=f"Non-empty body with {type(spec.payload.body).__name__}",
                        repair_hint="Remove the payload body or change target.method to POST/PUT/PATCH."
                    )
                )

        # 4. Content-Type and payload.type agreement
        headers_lower = {k.lower(): v for k, v in spec.headers.items()}
        content_type = headers_lower.get("content-type")
        if spec.payload.type == "json" and method_upper in ("POST", "PUT", "PATCH"):
            if content_type and "application/json" not in content_type:
                warnings.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CROSS_FIELD_CONTENT_TYPE_MISMATCH,
                        stage=StageName.CROSS_FIELD,
                        path="headers.Content-Type",
                        message=f"payload.type is 'json' but Content-Type is '{content_type}'",
                        severity=Severity.WARNING,
                        expected="application/json",
                        received=content_type,
                        repair_hint="Set headers['Content-Type'] to 'application/json'."
                    )
                )

        # 5. Template variable inspection for malformed syntax
        # Serialize payload body to string for regex scanning
        serialized_target = spec.target.endpoint
        if spec.payload.body is not None:
            if isinstance(spec.payload.body, (dict, list)):
                serialized_target += " " + json.dumps(spec.payload.body)
            else:
                serialized_target += " " + str(spec.payload.body)

        for key, val in spec.headers.items():
            serialized_target += f" {val}"

        # Detect malformed unclosed tokens (e.g. {{username without }})
        # Simple algorithm: count occurrences of "{{" vs "}}"
        open_count = serialized_target.count("{{")
        close_count = serialized_target.count("}}")
        if open_count != close_count:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CROSS_FIELD_MALFORMED_VARIABLE_TOKEN,
                    stage=StageName.CROSS_FIELD,
                    path="payload.body",
                    message=f"Malformed variable interpolation detected: {open_count} '{{{{' tokens but {close_count} '}}}}' tokens",
                    severity=Severity.ERROR,
                    expected="Matching {{variable}} syntax",
                    received="Mismatched variable delimiters",
                    repair_hint="Ensure all variable references are properly closed with '}}'."
                )
            )

        return errors, warnings
