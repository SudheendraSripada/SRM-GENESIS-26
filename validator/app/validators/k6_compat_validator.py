import re
from typing import List, Tuple, Dict, Any
from app.models.test_spec import TestSpec, ThresholdRule
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class K6CompatibilityValidator:
    """
    Stage 7: k6 Compatibility Gate.
    - Validates execution strategy maps to supported k6 executors (ramping-vus, constant-vus, arrival-rate).
    - Checks threshold metrics against k6 standard metric registry.
    - Validates threshold expression syntax and operator validity.
    """

    SUPPORTED_EXECUTORS = frozenset({"stages", "constant", "arrival_rate"})
    VALID_K6_METRICS = frozenset({
        "http_req_duration",
        "http_req_failed",
        "http_reqs",
        "http_req_connecting",
        "http_req_tls_handshaking",
        "http_req_waiting",
        "http_req_receiving",
        "iteration_duration",
        "checks",
        "vus",
        "vus_max"
    })
    VALID_OPERATORS = frozenset({"<", "<=", ">", ">=", "=="})
    _THRESHOLD_EXPR_RE = re.compile(r"^(?:(p\(\s*\d+\s*\)|avg|min|max|med|rate|count)\s*)?([<>]=?|==)\s*(\d+(?:\.\d+)?(?:s|ms|m)?)$")

    @classmethod
    def validate(cls, spec: TestSpec) -> Tuple[List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        # 1. Check load execution strategy
        strategy = spec.load.strategy.lower()
        if strategy not in cls.SUPPORTED_EXECUTORS:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.K6_UNSUPPORTED_EXECUTOR,
                    stage=StageName.K6_COMPATIBILITY,
                    path="load.strategy",
                    message=f"Requested strategy '{spec.load.strategy}' cannot be mapped to a standard k6 executor",
                    severity=Severity.ERROR,
                    expected=f"One of {sorted(list(cls.SUPPORTED_EXECUTORS))}",
                    received=spec.load.strategy,
                    repair_hint="Set 'load.strategy' to 'stages' or 'constant'."
                )
            )

        # 2. Thresholds validation
        if isinstance(spec.thresholds, list):
            for idx, item in enumerate(spec.thresholds):
                if isinstance(item, ThresholdRule):
                    metric = item.metric
                    operator = item.operator
                    percentile = item.percentile

                    if metric not in cls.VALID_K6_METRICS and not metric.startswith("custom_"):
                        warnings.append(
                            ValidationErrorItem(
                                code=ErrorCatalog.K6_INVALID_THRESHOLD_METRIC,
                                stage=StageName.K6_COMPATIBILITY,
                                path=f"thresholds[{idx}].metric",
                                message=f"Metric '{metric}' is not a standard k6 metric (e.g. http_req_duration)",
                                severity=Severity.WARNING,
                                expected=f"Standard k6 metric like {list(cls.VALID_K6_METRICS)[:4]}",
                                received=metric,
                                repair_hint="Use 'http_req_duration' or 'http_req_failed'."
                            )
                        )

                    if operator not in cls.VALID_OPERATORS:
                        errors.append(
                            ValidationErrorItem(
                                code=ErrorCatalog.K6_INVALID_THRESHOLD_SYNTAX,
                                stage=StageName.K6_COMPATIBILITY,
                                path=f"thresholds[{idx}].operator",
                                message=f"Comparison operator '{operator}' is invalid for k6 thresholds",
                                severity=Severity.ERROR,
                                expected="<, <=, >, >=, ==",
                                received=operator,
                                repair_hint="Use a valid comparison operator like '<' or '<='."
                            )
                        )

                    if percentile is not None and not (1 <= percentile <= 100):
                        errors.append(
                            ValidationErrorItem(
                                code=ErrorCatalog.K6_INVALID_THRESHOLD_SYNTAX,
                                stage=StageName.K6_COMPATIBILITY,
                                path=f"thresholds[{idx}].percentile",
                                message=f"Percentile must be between 1 and 100, got {percentile}",
                                severity=Severity.ERROR,
                                expected="1-100",
                                received=str(percentile),
                                repair_hint="Set percentile to 90, 95, or 99."
                            )
                        )

        elif isinstance(spec.thresholds, dict):
            for metric, expr in spec.thresholds.items():
                if metric not in cls.VALID_K6_METRICS and not metric.startswith("custom_"):
                    warnings.append(
                        ValidationErrorItem(
                            code=ErrorCatalog.K6_INVALID_THRESHOLD_METRIC,
                            stage=StageName.K6_COMPATIBILITY,
                            path=f"thresholds.{metric}",
                            message=f"Metric '{metric}' is not a standard k6 metric",
                            severity=Severity.WARNING,
                            expected="http_req_duration, http_req_failed, etc.",
                            received=metric,
                            repair_hint="Use standard metric name."
                        )
                    )

                # Verify expression syntax, e.g. "p(95)<500", "rate<0.01"
                expr_str = str(expr).strip()
                if not cls._THRESHOLD_EXPR_RE.match(expr_str):
                    errors.append(
                        ValidationErrorItem(
                            code=ErrorCatalog.K6_INVALID_THRESHOLD_SYNTAX,
                            stage=StageName.K6_COMPATIBILITY,
                            path=f"thresholds.{metric}",
                            message=f"Threshold expression '{expr_str}' does not conform to k6 syntax",
                            severity=Severity.ERROR,
                            expected="e.g. 'p(95)<500' or 'rate<0.02'",
                            received=expr_str,
                            repair_hint="Format threshold as 'p(95)<500' or 'rate<0.01'."
                        )
                    )

        # 3. Auth compatibility
        auth_type = spec.auth.type.lower()
        if auth_type not in ("none", "bearer", "basic", "custom"):
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.K6_UNSUPPORTED_AUTH_TYPE,
                    stage=StageName.K6_COMPATIBILITY,
                    path="auth.type",
                    message=f"Auth type '{spec.auth.type}' is not natively supported",
                    severity=Severity.ERROR,
                    expected="none, bearer, basic",
                    received=spec.auth.type,
                    repair_hint="Set auth.type to 'bearer', 'basic', or 'none'."
                )
            )

        return errors, warnings
