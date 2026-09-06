import re
from typing import List, Tuple
from urllib.parse import urlparse
from app.models.test_spec import TestSpec
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class ConstraintValidator:
    """
    Stage 3: Primitive & Field-Level Constraints.
    - O(1) membership in pre-allocated method and protocol sets.
    - Non-negative and minimum value boundary checks.
    - Strict URL scheme and host syntax validation.
    """

    ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
    ALLOWED_PROTOCOLS = frozenset({"http", "https", "grpc", "websocket"})

    @classmethod
    def validate(cls, spec: TestSpec) -> Tuple[List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        # 1. HTTP Method constraint
        method_upper = spec.target.method.upper()
        if method_upper not in cls.ALLOWED_METHODS:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_INVALID_METHOD,
                    stage=StageName.CONSTRAINTS,
                    path="target.method",
                    message=f"HTTP method '{spec.target.method}' is not valid",
                    severity=Severity.ERROR,
                    expected=f"One of {sorted(list(cls.ALLOWED_METHODS))}",
                    received=spec.target.method,
                    repair_hint="Set 'target.method' to a standard HTTP verb (e.g. GET, POST, PUT, DELETE)."
                )
            )

        # 2. Protocol constraint
        if spec.test.protocol.lower() not in cls.ALLOWED_PROTOCOLS:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_INVALID_PROTOCOL,
                    stage=StageName.CONSTRAINTS,
                    path="test.protocol",
                    message=f"Protocol '{spec.test.protocol}' is unsupported",
                    severity=Severity.ERROR,
                    expected=f"One of {sorted(list(cls.ALLOWED_PROTOCOLS))}",
                    received=spec.test.protocol,
                    repair_hint="Set 'test.protocol' to 'http' or 'https'."
                )
            )

        # 3. URL Syntax
        try:
            parsed_url = urlparse(spec.target.base_url)
            if parsed_url.scheme not in ("http", "https"):
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CONSTRAINT_INVALID_URL,
                        stage=StageName.CONSTRAINTS,
                        path="target.base_url",
                        message=f"Target URL scheme must be http or https, got '{parsed_url.scheme}'",
                        severity=Severity.ERROR,
                        expected="http or https URL",
                        received=spec.target.base_url,
                        repair_hint="Prefix target base_url with http:// or https://."
                    )
                )
            if not parsed_url.netloc:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CONSTRAINT_INVALID_URL,
                        stage=StageName.CONSTRAINTS,
                        path="target.base_url",
                        message="Target base_url missing valid host domain/network location",
                        severity=Severity.ERROR,
                        expected="Valid domain name or IP host",
                        received=spec.target.base_url,
                        repair_hint="Provide a valid host, e.g. https://staging.internal.net"
                    )
                )
        except Exception as exc:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_INVALID_URL,
                    stage=StageName.CONSTRAINTS,
                    path="target.base_url",
                    message=f"Malformed URL string: {str(exc)}",
                    severity=Severity.ERROR,
                    expected="RFC 3986 parseable URL",
                    received=spec.target.base_url,
                    repair_hint="Provide a syntactically valid URL."
                )
            )

        # 4. Load constraints
        if spec.load.start_vus < 0:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_VUS_RANGE,
                    stage=StageName.CONSTRAINTS,
                    path="load.start_vus",
                    message=f"start_vus cannot be negative, got {spec.load.start_vus}",
                    severity=Severity.ERROR,
                    expected=">= 0",
                    received=str(spec.load.start_vus),
                    repair_hint="Set 'load.start_vus' to a non-negative integer (e.g. 1 or 10)."
                )
            )

        if spec.load.target_vus <= 0:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_VUS_RANGE,
                    stage=StageName.CONSTRAINTS,
                    path="load.target_vus",
                    message=f"target_vus must be positive, got {spec.load.target_vus}",
                    severity=Severity.ERROR,
                    expected=">= 1",
                    received=str(spec.load.target_vus),
                    repair_hint="Set 'load.target_vus' to at least 1."
                )
            )

        if spec.load.duration_seconds < 1:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.CONSTRAINT_DURATION_RANGE,
                    stage=StageName.CONSTRAINTS,
                    path="load.duration_seconds",
                    message=f"duration_seconds must be >= 1, got {spec.load.duration_seconds}",
                    severity=Severity.ERROR,
                    expected=">= 1 second",
                    received=str(spec.load.duration_seconds),
                    repair_hint="Set 'load.duration_seconds' to at least 1."
                )
            )

        # 5. Stage items constraints
        for idx, stage in enumerate(spec.stages):
            if stage.duration_seconds <= 0:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CONSTRAINT_INVALID_STAGE,
                        stage=StageName.CONSTRAINTS,
                        path=f"stages[{idx}].duration_seconds",
                        message=f"Stage {idx} duration must be positive, got {stage.duration_seconds}",
                        severity=Severity.ERROR,
                        expected="> 0 seconds",
                        received=str(stage.duration_seconds),
                        repair_hint=f"Increase stage {idx} duration to at least 1 second."
                    )
                )
            if stage.target_vus < 0:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.CONSTRAINT_INVALID_STAGE,
                        stage=StageName.CONSTRAINTS,
                        path=f"stages[{idx}].target_vus",
                        message=f"Stage {idx} target_vus cannot be negative, got {stage.target_vus}",
                        severity=Severity.ERROR,
                        expected=">= 0",
                        received=str(stage.target_vus),
                        repair_hint=f"Set stages[{idx}].target_vus to 0 or greater."
                    )
                )

        return errors, warnings
