import json
from typing import Dict, List
from urllib.parse import urlparse

from performance_testing_ai.models.requirement import HttpMethod, ThresholdSpec
from performance_testing_ai.models.performance_plan import StageSpec
from performance_testing_ai.models.test_specification import HttpStepSpec, TestSpecification
from performance_testing_ai.execution.validator import parse_duration_seconds

class CompilationError(ValueError):
    """Raised when a TestSpecification cannot be safely or deterministically compiled into k6 JavaScript."""
    pass

def _validate_compilation_input(spec: TestSpecification) -> None:
    """
    Lightweight defensive checks before compilation to prevent unsafe, ambiguous,
    or broken code generation. The compiler does not auto-fix invalid input.
    """
    if not spec.target or not spec.target.base_url:
        raise CompilationError("Cannot compile TestSpecification: target.base_url is missing or empty.")

    parsed = urlparse(spec.target.base_url)
    if (parsed.scheme or "").lower() not in ("http", "https") or not parsed.netloc:
        raise CompilationError(
            f"Cannot compile TestSpecification: target.base_url '{spec.target.base_url}' is invalid. "
            "Must be an absolute URL with 'http' or 'https' scheme."
        )

    if not spec.load:
        raise CompilationError("Cannot compile TestSpecification: load contains no stages.")

    max_vus = spec.safety_constraints.max_vus if spec.safety_constraints else 0
    if max_vus <= 0:
        raise CompilationError("Cannot compile TestSpecification: safety_constraints.max_vus must be > 0.")

    for idx, stage in enumerate(spec.load):
        try:
            sec = parse_duration_seconds(stage.duration)
            if sec <= 0:
                raise ValueError("Stage duration must be > 0s")
        except ValueError as exc:
            raise CompilationError(
                f"Cannot compile TestSpecification: load[{idx}].duration '{stage.duration}' is invalid: {str(exc)}"
            )

        if stage.target_vus < 0:
            raise CompilationError(
                f"Cannot compile TestSpecification: load[{idx}].target_vus cannot be negative ({stage.target_vus})."
            )
        if stage.target_vus > max_vus:
            raise CompilationError(
                f"Cannot compile TestSpecification: load[{idx}].target_vus ({stage.target_vus}) "
                f"exceeds safety limit max_vus ({max_vus})."
            )

    if not spec.request_sequence:
        raise CompilationError("Cannot compile TestSpecification: request_sequence is empty.")

    valid_methods = {m.value for m in HttpMethod}
    for idx, step in enumerate(spec.request_sequence):
        if not step.endpoint or not step.endpoint.startswith("/"):
            raise CompilationError(
                f"Cannot compile TestSpecification: request_sequence[{idx}].endpoint must start with '/', "
                f"got '{step.endpoint}'."
            )

        method_str = step.method.value if isinstance(step.method, HttpMethod) else str(step.method)
        if method_str not in valid_methods:
            raise CompilationError(
                f"Cannot compile TestSpecification: request_sequence[{idx}].method '{method_str}' is unsupported."
            )

    for idx, t in enumerate(spec.thresholds):
        if t.value < 0:
            raise CompilationError(
                f"Cannot compile TestSpecification: thresholds[{idx}].value must be non-negative, got {t.value}."
            )

def _compile_single_threshold(t: ThresholdSpec) -> str:
    """
    Translates a single ThresholdSpec into k6 threshold expression syntax.
    Example:
      p95 < 500ms -> 'p(95)<500'
      rate < 0.01 -> 'rate<0.01'
    """
    operator = t.operator or "<"
    val = t.value

    metric_lower = t.metric.lower()
    is_failure_metric = "failed" in metric_lower or "error" in metric_lower

    if is_failure_metric:
        # If expressed as percentage > 1.0 (e.g. 5%), normalize to rate fraction (0.05)
        if val > 1.0 and t.unit == "%":
            rate_val = val / 100.0
        else:
            rate_val = val
        return f"rate{operator}{rate_val}"

    val_formatted = int(val) if isinstance(val, float) and val.is_integer() else val

    if t.aggregation:
        agg_lower = t.aggregation.lower()
        if agg_lower.startswith("p") and agg_lower[1:].isdigit():
            percentile = agg_lower[1:]
            return f"p({percentile}){operator}{val_formatted}"
        elif agg_lower in ("avg", "min", "max", "med"):
            return f"{agg_lower}{operator}{val_formatted}"
        elif agg_lower == "rate":
            return f"rate{operator}{val_formatted}"

    return f"{operator}{val_formatted}"

def _generate_options(spec: TestSpecification) -> str:
    """Generates the export const options block for k6."""
    lines = ["export const options = {"]

    # 1. Stages
    lines.append("    stages: [")
    for stage in spec.load:
        lines.append(f"        {{ duration: {json.dumps(stage.duration)}, target: {stage.target_vus} }},")
    lines.append("    ],")

    # 2. Thresholds
    if spec.thresholds:
        thresholds_by_metric: Dict[str, List[str]] = {}
        for t in spec.thresholds:
            rule_str = _compile_single_threshold(t)
            thresholds_by_metric.setdefault(t.metric, []).append(rule_str)

        lines.append("    thresholds: {")
        for metric, rules in thresholds_by_metric.items():
            rules_json = json.dumps(rules)
            lines.append(f"        {json.dumps(metric)}: {rules_json},")
        lines.append("    },")

    lines.append("};")
    return "\n".join(lines)

def _generate_http_step(
    idx: int,
    step: HttpStepSpec,
    default_headers: Dict[str, str],
    timeout_seconds: float,
) -> str:
    """Generates an individual HTTP request execution step inside the default function."""
    lines = []
    step_clean_name = (step.name or f"Step {idx + 1}").replace("\n", " ").strip()
    lines.append(f"    // Step {idx + 1}: {step_clean_name}")
    lines.append("    {")

    # Merge headers
    merged_headers = dict(default_headers)
    merged_headers.update(step.headers)

    params_obj: Dict[str, object] = {}
    if merged_headers:
        params_obj["headers"] = merged_headers
    if timeout_seconds > 0:
        t_val = int(timeout_seconds) if timeout_seconds.is_integer() else timeout_seconds
        params_obj["timeout"] = f"{t_val}s"

    params_json = json.dumps(params_obj, indent=12)
    # Indent params properly
    params_lines = params_json.split("\n")
    lines.append("        const params = " + params_lines[0])
    for pl in params_lines[1:]:
        lines.append("        " + pl + (";" if pl == params_lines[-1] else ""))

    # Prepare URL
    endpoint_json = json.dumps(step.endpoint)
    url_expr = f"BASE_URL + {endpoint_json}"

    # Prepare payload if applicable
    method = step.method if isinstance(step.method, HttpMethod) else HttpMethod(step.method)
    has_payload = method in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH)

    if has_payload and step.payload_schema:
        payload_json = json.dumps(step.payload_schema, indent=12)
        payload_lines = payload_json.split("\n")
        lines.append("        const payload = JSON.stringify(" + payload_lines[0])
        for pl in payload_lines[1:]:
            lines.append("        " + pl + (");" if pl == payload_lines[-1] else ""))
        payload_arg = "payload"
    elif has_payload:
        payload_arg = "null"
    else:
        payload_arg = None

    # Call http method
    if method == HttpMethod.GET:
        lines.append(f"        const res = http.get({url_expr}, params);")
    elif method == HttpMethod.POST:
        lines.append(f"        const res = http.post({url_expr}, {payload_arg}, params);")
    elif method == HttpMethod.PUT:
        lines.append(f"        const res = http.put({url_expr}, {payload_arg}, params);")
    elif method == HttpMethod.PATCH:
        lines.append(f"        const res = http.patch({url_expr}, {payload_arg}, params);")
    elif method == HttpMethod.DELETE:
        lines.append(f"        const res = http.del({url_expr}, null, params);")

    # Status check
    if step.expected_status_codes:
        codes = step.expected_status_codes
        if len(codes) == 1:
            check_msg = f"status is {codes[0]}"
            check_fn = f"(r) => r.status === {codes[0]}"
        else:
            code_str = " or ".join(str(c) for c in codes)
            check_msg = f"status is {code_str}"
            check_fn = f"(r) => {json.dumps(codes)}.includes(r.status)"

        lines.append("        check(res, {")
        lines.append(f"            {json.dumps(check_msg)}: {check_fn},")
        lines.append("        });")

    # Think time
    if step.think_time_seconds > 0:
        sleep_val = (
            int(step.think_time_seconds)
            if step.think_time_seconds.is_integer()
            else step.think_time_seconds
        )
        lines.append(f"        sleep({sleep_val});")

    lines.append("    }")
    return "\n".join(lines)

def compile_k6_script(spec: TestSpecification) -> str:
    """
    Deterministic TestSpecification -> k6 JavaScript Compiler (Phase 3B).

    Translates a validated TestSpecification into a standalone, reproducible k6 JavaScript script.
    
    Guarantees:
    - Pure function: zero side effects, zero network calls, zero shell/k6 execution, no file writes.
    - 100% deterministic: identical input produces identical byte-for-byte JavaScript code.
    - Read-only: never modifies the input TestSpecification.
    - Safe escaping: all string inputs are securely serialized using JSON/JS escaping.
    - Defensive: rejects invalid specifications without attempting silent repairs.

    Args:
        spec: The validated TestSpecification to compile.

    Returns:
        Complete k6 JavaScript test script as a string.

    Raises:
        CompilationError: If the specification violates structural or safety constraints.
    """
    _validate_compilation_input(spec)

    base_url = spec.target.base_url.rstrip("/")
    timeout = spec.target.timeout_seconds
    default_headers = spec.target.default_headers or {}

    sections: List[str] = [
        "// Auto-generated by Performance Testing AI (IEEE Genesis)",
        "// Mode: Deterministic k6 Script Compiler (Phase 3B)",
        "",
        "import http from 'k6/http';",
        "import { check, sleep } from 'k6';",
        "",
        f"const BASE_URL = {json.dumps(base_url)};",
        "",
        _generate_options(spec),
        "",
        "export default function () {",
    ]

    for idx, step in enumerate(spec.request_sequence):
        sections.append(_generate_http_step(idx, step, default_headers, timeout))

    sections.append("}")
    sections.append("")  # Final newline

    return "\n".join(sections)
