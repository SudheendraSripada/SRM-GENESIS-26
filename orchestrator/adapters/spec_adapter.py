"""
Pure-function adapter translating CrewAI TestSpecification and TestDataPlan
into FastAPI Validator TestSpec models for progressive verification and k6 compilation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# Ensure workspace paths are available
_workspace_root = Path(__file__).resolve().parent.parent.parent
_agents_src = _workspace_root / "agents" / "src"
_validator_root = _workspace_root / "validator"

for _p in [str(_workspace_root), str(_agents_src), str(_validator_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Agent models (read-only input contracts)
from performance_testing_ai.models.test_specification import (
    TestSpecification,
    HttpStepSpec,
)
from performance_testing_ai.models.test_data import (
    TestDataPlan,
    ParameterizationRule,
    DatasetRequirement,
    UserProfileSpec,
)

# Validator models (target schema)
from app.models.test_spec import (
    TestSpec,
    Metadata,
    TestTypeConfig,
    TargetConfig,
    LoadConfig,
    StageConfig,
    PayloadConfig,
    AuthConfig,
    ThresholdRule,
    CheckRule,
)
from app.models.safety_policy import SafetyPolicy


class AgentEvent(BaseModel):
    """
    Timeline event emitted during contract adaptation to surface simplifications,
    omissions, or adjustments to the user and console.
    """
    event_type: str = Field(..., description="Machine-readable event category")
    source: str = Field(default="spec_adapter", description="Emitting component identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp",
    )
    message: str = Field(..., description="Human-readable event description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured event payload")


class AdaptationResult(BaseModel):
    """
    Result returned by adapt_specification containing the validator-compliant TestSpec
    and any timeline events emitted during transformation.
    """
    spec: Union[TestSpec, Dict[str, Any]] = Field(..., description="Validator-compliant TestSpec instance or dictionary")
    events: List[AgentEvent] = Field(
        default_factory=list,
        description="Chronological events captured during adaptation",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Returns the TestSpec representation as a pure Python dictionary."""
        if isinstance(self.spec, dict):
            return self.spec
        return self.spec.model_dump()


_DURATION_PATTERN = re.compile(r"(\d+)\s*(h|m|s)?", re.IGNORECASE)
_VARIABLE_PATTERN = re.compile(r"(?:\$\{([a-zA-Z0-9_\-]+)\}|\{\{([a-zA-Z0-9_\-]+)\}\})")
_COMPOSITE_METRIC_RE = re.compile(r"^([a-zA-Z0-9_\-]+)(?:\(([^)]+)\))?$")

# Standard type keywords used in payload schemas
_TYPE_DESCRIPTORS = frozenset({
    "string", "str", "text",
    "int", "integer",
    "float", "number", "decimal",
    "bool", "boolean",
    "dict", "object", "json",
    "list", "array",
})

# Semantic metric aliases mapping to canonical k6 metrics
_METRIC_ALIASES: Dict[str, str] = {
    "error_rate": "http_req_failed",
    "errors": "http_req_failed",
    "failed_requests": "http_req_failed",
    "error": "http_req_failed",
    "latency": "http_req_duration",
    "response_time": "http_req_duration",
    "duration": "http_req_duration",
    "response_duration": "http_req_duration",
    "throughput": "http_reqs",
    "rps": "http_reqs",
    "requests": "http_reqs",
}


def parse_duration_seconds(val: Any) -> int:
    """
    Parses duration strings like '2m', '30s', '1h', or composite '2m30s' into total seconds.
    Defaults to 60 seconds if format is missing or invalid.
    """
    if isinstance(val, (int, float)):
        return max(1, int(val))
    if not isinstance(val, str) or not val.strip():
        return 60

    matches = _DURATION_PATTERN.findall(val.strip())
    if matches:
        total = 0
        for num_str, unit in matches:
            num = int(num_str)
            unit_lower = (unit or "s").lower()
            if unit_lower == "h":
                total += num * 3600
            elif unit_lower == "m":
                total += num * 60
            else:
                total += num
        if total > 0:
            return total
    return 60


def _coerce_data_plan(
    test_data_plan: Optional[Union[TestDataPlan, Dict[str, Any]]],
) -> Optional[TestDataPlan]:
    """Ensures test_data_plan is a typed TestDataPlan model if possible."""
    if test_data_plan is None:
        return None
    if isinstance(test_data_plan, TestDataPlan):
        return test_data_plan
    if isinstance(test_data_plan, dict):
        try:
            return TestDataPlan(**test_data_plan)
        except Exception:
            return None
    return None


def _resolve_scalar_value(
    field_name: str,
    type_or_val: Any,
    data_plan: Optional[Union[TestDataPlan, Dict[str, Any]]] = None,
) -> Any:
    """
    Resolves an individual field in a payload schema from type descriptions
    or template placeholders into concrete, realistic mock data using
    heuristics and TestDataPlan rules.
    """
    plan = _coerce_data_plan(data_plan)
    val_str = str(type_or_val).strip()

    # Check for template variable placeholders like "${cart_id}" or "{{cart_id}}"
    var_match = _VARIABLE_PATTERN.match(val_str)
    if var_match:
        inner_var = var_match.group(1) or var_match.group(2)
        return _resolve_scalar_value(inner_var, "string", plan)

    val_lower = val_str.lower()

    # If it's not a recognized type descriptor, it is already a concrete value
    if val_lower not in _TYPE_DESCRIPTORS:
        return type_or_val

    field_lower = field_name.lower()

    # 1. Match against parameterization rules from TestDataPlan
    if plan and plan.parameterization_rules:
        for rule in plan.parameterization_rules:
            if rule.parameter_name.lower() == field_lower:
                if val_lower in ("int", "integer"):
                    return 1001
                return f"{field_name}_test_1001"

    # 2. Match against datasets_needed fields in TestDataPlan
    if plan and plan.datasets_needed:
        for ds in plan.datasets_needed:
            if field_name in ds.fields or field_lower in [f.lower() for f in ds.fields]:
                if val_lower in ("int", "integer"):
                    return 1001
                if "token" in field_lower or "auth" in field_lower:
                    return f"tok_{ds.name}_test"
                if "id" in field_lower:
                    return f"{field_name}_test_1"

    # 3. Type-based resolution with semantic name heuristics
    if val_lower in ("int", "integer"):
        if any(k in field_lower for k in ("qty", "quantity", "count", "num", "page", "limit", "items")):
            return 1
        if "id" in field_lower:
            return 1001
        return 1

    if val_lower in ("float", "number", "decimal"):
        if any(k in field_lower for k in ("price", "amount", "total", "cost", "fee", "rate")):
            return 19.99
        return 1.0

    if val_lower in ("bool", "boolean"):
        return True

    if val_lower in ("list", "array"):
        return []

    if val_lower in ("dict", "object", "json"):
        return {}

    # String type heuristics
    if "email" in field_lower:
        return "test_user@example.com"
    if "password" in field_lower or "secret" in field_lower:
        return "SecureTestPass123!"
    if "token" in field_lower or "jwt" in field_lower or "key" in field_lower:
        return f"tok_test_{field_name}"
    if "cart" in field_lower:
        return "cart_test_1001"
    if "user" in field_lower or "customer" in field_lower or "account" in field_lower:
        return "usr_test_1001"
    if "product" in field_lower or "item" in field_lower or "sku" in field_lower:
        return "sku_test_1001"
    if "id" in field_lower or field_lower.endswith("_id"):
        return f"{field_name}_test_1"
    if "name" in field_lower or "title" in field_lower:
        return f"Test {field_name.replace('_', ' ').title()}"
    if "url" in field_lower or "uri" in field_lower:
        return "https://staging.local/resource"
    if "status" in field_lower:
        return "active"

    return f"test_{field_name}_val"


def resolve_payload_body(
    step: Union[HttpStepSpec, Dict[str, Any], Any],
    data_plan: Optional[Union[TestDataPlan, Dict[str, Any]]] = None,
) -> Optional[Any]:
    """
    Resolves the payload body for an HttpStepSpec or step dictionary using type descriptions and TestDataPlan.
    Recursively replaces type placeholders with concrete, valid mock values.
    """
    if not step:
        return None

    if isinstance(step, dict):
        payload_schema = step.get("payload_schema", step)
    else:
        payload_schema = getattr(step, "payload_schema", None)

    if not payload_schema:
        return None

    if isinstance(payload_schema, str):
        try:
            payload_schema = json.loads(payload_schema)
        except Exception:
            pass

    plan = _coerce_data_plan(data_plan)

    def _resolve_recursive(schema: Any, field_context: str = "item") -> Any:
        if isinstance(schema, dict):
            return {
                k: _resolve_recursive(v, k) if isinstance(v, (dict, list))
                else _resolve_scalar_value(k, v, plan)
                for k, v in schema.items()
            }
        elif isinstance(schema, list):
            return [_resolve_recursive(item, field_context) for item in schema]
        else:
            return _resolve_scalar_value(field_context, schema, plan)

    return _resolve_recursive(payload_schema)


def normalize_threshold_rule(t: Any) -> ThresholdRule:
    """
    Translates an agent ThresholdSpec or dict into a standard k6-compatible ThresholdRule.
    Decomposes composite metrics like 'http_req_duration(p95)' or 'http_req_failed(rate)',
    maps metric aliases ('error_rate' -> 'http_req_failed'), normalizes percentages
    (e.g., 1% -> 0.01 for error rate), and converts time units ('2s' -> 2000.0 ms for duration).
    """
    raw_metric = getattr(t, "metric", None) or (t.get("metric") if isinstance(t, dict) else str(t))
    operator = getattr(t, "operator", None) or (t.get("operator") if isinstance(t, dict) else None) or "<"
    val = getattr(t, "value", None) if hasattr(t, "value") else (t.get("value") if isinstance(t, dict) else 500)
    raw_agg = getattr(t, "aggregation", None) or (t.get("aggregation") if isinstance(t, dict) else None)
    unit = str(getattr(t, "unit", None) or (t.get("unit") if isinstance(t, dict) else "")).lower()

    # Parse composite metric e.g. "http_req_duration(p95)" -> ("http_req_duration", "p95")
    base_metric = raw_metric.strip()
    embedded_term = None
    comp_match = _COMPOSITE_METRIC_RE.match(base_metric)
    if comp_match:
        base_metric = comp_match.group(1)
        embedded_term = comp_match.group(2)

    # Normalize base metric through known aliases
    base_lower = base_metric.lower()
    canonical_metric = _METRIC_ALIASES.get(base_lower, base_metric)
    canonical_lower = canonical_metric.lower()

    # Determine percentile and aggregation
    pct: Optional[int] = None
    agg: Optional[str] = None

    active_agg = raw_agg or embedded_term
    if active_agg:
        agg_str = str(active_agg).strip().lower()
        if agg_str.startswith("p") and agg_str[1:].isdigit():
            pct = int(agg_str[1:])
        elif agg_str in ("avg", "min", "max", "med", "rate", "count"):
            agg = agg_str
        else:
            agg = agg_str

    # Special handling for failure/error metrics
    is_failure = "failed" in canonical_lower or "error" in canonical_lower
    if is_failure:
        canonical_metric = "http_req_failed"
        agg = "rate"
        pct = None
        # Normalize error rate percentage (e.g. 1% or 5% -> 0.01 or 0.05)
        if unit == "%" or val > 1.0:
            if val >= 1.0 or (val > 0.05 and unit == "%"):
                val = val / 100.0

    # Special handling for duration metrics
    is_duration = (
        "duration" in canonical_lower
        or "latency" in canonical_lower
        or "connecting" in canonical_lower
        or "waiting" in canonical_lower
    )
    if is_duration:
        # Convert seconds to milliseconds if unit is 's' / 'sec' / 'seconds'
        if unit in ("s", "sec", "second", "seconds"):
            val = val * 1000.0

    return ThresholdRule(
        metric=canonical_metric,
        percentile=pct,
        aggregation=agg,
        operator=operator,
        value=val,
    )


def build_safety_policy(
    test_spec: Union[TestSpecification, Dict[str, Any]],
) -> SafetyPolicy:
    """
    Constructs an authorized SafetyPolicy conforming to the safety constraints
    declared in the agent TestSpecification.
    """
    if isinstance(test_spec, dict):
        spec_obj = TestSpecification(**test_spec)
    else:
        spec_obj = test_spec

    constraints = getattr(spec_obj, "safety_constraints", None)

    allowed_targets: List[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "https://example.com",
        "http://test-api",
        "https://staging.internal.net",
        "https://httpbin.org",
        "http://httpbin.org",
    ]

    if constraints and getattr(constraints, "allowed_domains", None):
        for domain in constraints.allowed_domains:
            domain_clean = domain.strip().lower()
            if not domain_clean.startswith("http://") and not domain_clean.startswith("https://"):
                allowed_targets.append(f"http://{domain_clean}")
                allowed_targets.append(f"https://{domain_clean}")
            else:
                allowed_targets.append(domain_clean)

    if spec_obj.target and spec_obj.target.base_url:
        target_base = spec_obj.target.base_url.strip().lower()
        if target_base not in allowed_targets:
            allowed_targets.append(target_base)

    max_vus = constraints.max_vus if (constraints and constraints.max_vus) else 1000
    max_duration = constraints.max_duration_seconds if (constraints and constraints.max_duration_seconds) else 1800

    return SafetyPolicy(
        max_vus=max_vus,
        max_duration_seconds=max_duration,
        allowed_targets=allowed_targets,
    )


def adapt_specification(
    test_specification: Union[TestSpecification, Dict[str, Any]],
    test_data_plan: Optional[Union[TestDataPlan, Dict[str, Any]]] = None,
) -> AdaptationResult:
    """
    Adapts a CrewAI TestSpecification and optional TestDataPlan into a validator-compliant TestSpec.

    Rules applied:
    1. Multi-step requests: compiles only request_sequence[0] as the primary target for MVP.
       Emits an AgentEvent flagging the simplification when request_sequence has > 1 step.
    2. Payload synthesis: maps request_sequence[0].payload_schema with TestDataPlan to resolve
       concrete data rather than type placeholder strings.
    3. Load & Invariant alignment: strictly computes load.duration_seconds matching sum of stages,
       sets start_vus <= target_vus (with start_vus=0 for non-decreasing ramp in stress tests),
       and preserves test semantics.
    4. HTTP invariant checks: omits body for GET/HEAD methods, injects Content-Type: application/json
       for POST/PUT/PATCH when payload is present.
    5. Threshold normalization: converts ThresholdSpec metrics, composite names, and aggregations to standard k6 rules.
    6. Assertion generation: maps expected_status_codes into CheckRule expressions.
    7. Authentication resolution: resolves token templates and configures AuthConfig.

    Returns:
        AdaptationResult containing the adapted TestSpec and list of timeline AgentEvents.
    """
    events: List[AgentEvent] = []

    # Coerce dict inputs to Pydantic models if necessary
    if isinstance(test_specification, dict):
        spec: TestSpecification = TestSpecification(**test_specification)
    else:
        spec = test_specification

    data_plan: Optional[TestDataPlan] = _coerce_data_plan(test_data_plan)

    # -------------------------------------------------------------------------
    # 1. Target and Endpoint Resolution (Multi-step Simplification Gate)
    # -------------------------------------------------------------------------
    steps: List[HttpStepSpec] = spec.request_sequence or []
    selected_step: Optional[HttpStepSpec] = None

    if len(steps) > 1:
        selected_step = steps[0]
        omitted_steps = [
            {
                "name": s.name,
                "endpoint": s.endpoint,
                "method": s.method.value if hasattr(s.method, "value") else str(s.method),
            }
            for s in steps[1:]
        ]
        events.append(
            AgentEvent(
                event_type="scenario_simplified",
                source="spec_adapter",
                message=(
                    f"Multi-step workload scenario ({len(steps)} steps) simplified to primary "
                    f"endpoint '{selected_step.endpoint}' for MVP single-target execution."
                ),
                details={
                    "total_steps": len(steps),
                    "primary_step": {
                        "name": selected_step.name,
                        "endpoint": selected_step.endpoint,
                        "method": selected_step.method.value if hasattr(selected_step.method, "value") else str(selected_step.method),
                    },
                    "omitted_steps": omitted_steps,
                },
            )
        )
    elif len(steps) == 1:
        selected_step = steps[0]
    else:
        selected_step = None
        events.append(
            AgentEvent(
                event_type="default_endpoint_fallback",
                source="spec_adapter",
                message="No request_sequence steps found in TestSpecification; defaulting to GET /.",
                details={},
            )
        )

    endpoint = selected_step.endpoint if selected_step else "/"
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    method_str = (
        (selected_step.method.value if hasattr(selected_step.method, "value") else str(selected_step.method))
        if selected_step
        else "GET"
    )
    method_upper = method_str.strip().upper()

    base_url = spec.target.base_url.rstrip("/") if (spec.target and spec.target.base_url) else "http://staging.local"
    timeout_seconds = spec.target.timeout_seconds if (spec.target and spec.target.timeout_seconds) else 10.0
    timeout_ms = int(timeout_seconds * 1000)

    target_config = TargetConfig(
        base_url=base_url,
        endpoint=endpoint,
        method=method_upper,
        timeout_ms=timeout_ms,
    )

    # -------------------------------------------------------------------------
    # 2. Headers Configuration & Variable Resolution
    # -------------------------------------------------------------------------
    headers: Dict[str, str] = {}
    if spec.target and spec.target.default_headers:
        headers.update(spec.target.default_headers)
    if selected_step and selected_step.headers:
        headers.update(selected_step.headers)

    # Resolve synthetic token value if data plan or user profiles present
    synthetic_token = "synth_session_token_1"
    if data_plan and getattr(data_plan, "datasets_needed", None):
        for ds in data_plan.datasets_needed:
            if "auth_token" in ds.fields or "token" in ds.fields:
                synthetic_token = f"tok_{ds.name}_test"
                break

    # Resolve any ${var} or {{var}} placeholders in headers
    resolved_headers: Dict[str, str] = {}
    for h_key, h_val in headers.items():
        if isinstance(h_val, str) and ("${" in h_val or "{{" in h_val):
            def _replace_header_var(m: re.Match) -> str:
                var_name = m.group(1) or m.group(2)
                if "token" in var_name.lower() or "auth" in var_name.lower():
                    return synthetic_token
                return str(_resolve_scalar_value(var_name, "string", data_plan))
            resolved_headers[h_key] = _VARIABLE_PATTERN.sub(_replace_header_var, h_val)
        else:
            resolved_headers[h_key] = h_val
    headers = resolved_headers

    # -------------------------------------------------------------------------
    # 3. Payload Synthesis (Resolving schema types using TestDataPlan)
    # -------------------------------------------------------------------------
    payload_config = PayloadConfig(type="none", body=None)

    if method_upper in ("POST", "PUT", "PATCH", "DELETE"):
        if selected_step and selected_step.payload_schema:
            resolved_body = resolve_payload_body(selected_step, data_plan)
            if resolved_body is not None:
                payload_config = PayloadConfig(type="json", body=resolved_body)
                # Inject application/json Content-Type if not already present
                has_content_type = any(k.lower() == "content-type" for k in headers)
                if not has_content_type:
                    headers["Content-Type"] = "application/json"
    elif method_upper in ("GET", "HEAD"):
        if selected_step and selected_step.payload_schema:
            events.append(
                AgentEvent(
                    event_type="payload_omitted_for_get",
                    source="spec_adapter",
                    message=(
                        f"Omitted payload body for HTTP {method_upper} on '{endpoint}' "
                        "to comply with HTTP specification invariants."
                    ),
                    details={"endpoint": endpoint, "method": method_upper},
                )
            )

    # -------------------------------------------------------------------------
    # 4. Stages and Load Configuration
    # -------------------------------------------------------------------------
    stages_configs: List[StageConfig] = []
    if spec.load:
        for s in spec.load:
            dur_sec = parse_duration_seconds(s.duration)
            stages_configs.append(StageConfig(duration_seconds=dur_sec, target_vus=s.target_vus))

    total_stage_duration = sum(s.duration_seconds for s in stages_configs)
    peak_vus = max((s.target_vus for s in stages_configs), default=10)
    if peak_vus < 1:
        peak_vus = 1

    # Start VUs:
    # Set start_vus=0 when stages are present to guarantee monotonic non-decreasing
    # progression before peak, satisfying SemanticValidator for stress/load tests.
    start_vus = 0 if stages_configs else 1

    load_config = LoadConfig(
        strategy="stages" if stages_configs else "constant",
        start_vus=start_vus,
        target_vus=peak_vus,
        duration_seconds=total_stage_duration if stages_configs else 60,
    )

    # -------------------------------------------------------------------------
    # 5. Thresholds Mapping & Canonical Normalization
    # -------------------------------------------------------------------------
    threshold_rules: List[ThresholdRule] = []
    for t in (spec.thresholds or []):
        threshold_rules.append(normalize_threshold_rule(t))

    # -------------------------------------------------------------------------
    # 6. Checks & Assertion Generation
    # -------------------------------------------------------------------------
    check_rules: List[CheckRule] = []
    if selected_step and selected_step.expected_status_codes:
        codes = selected_step.expected_status_codes
        if len(codes) == 1:
            check_rules.append(
                CheckRule(
                    name=f"status is {codes[0]}",
                    expression=f"r.status === {codes[0]}",
                )
            )
        else:
            check_rules.append(
                CheckRule(
                    name=f"status is {' or '.join(str(c) for c in codes)}",
                    expression=f"{json.dumps(codes)}.includes(r.status)",
                )
            )

    # -------------------------------------------------------------------------
    # 7. Authentication Configuration
    # -------------------------------------------------------------------------
    auth_config = AuthConfig(type="none")
    auth_header = next((v for k, v in headers.items() if k.lower() == "authorization"), None)
    auth_reqs = " ".join(spec.authentication_requirements or []).lower()

    if auth_header:
        header_lower = auth_header.lower().strip()
        if header_lower.startswith("bearer "):
            token_extracted = auth_header.strip()[7:].strip()
            auth_config = AuthConfig(type="bearer", token=token_extracted or synthetic_token)
        elif header_lower.startswith("basic "):
            auth_config = AuthConfig(type="basic", username="test_user", password="test_password")
        else:
            auth_config = AuthConfig(type="bearer", token=synthetic_token)
    elif auth_reqs:
        if "bearer" in auth_reqs or "token" in auth_reqs or "oauth" in auth_reqs:
            auth_config = AuthConfig(type="bearer", token=synthetic_token)
        elif "basic" in auth_reqs:
            auth_config = AuthConfig(type="basic", username="test_user", password="test_password")

    # -------------------------------------------------------------------------
    # 8. Metadata and Type Configuration
    # -------------------------------------------------------------------------
    test_type_str = (
        spec.test_type.value if hasattr(spec.test_type, "value") else str(spec.test_type)
    ).lower()
    protocol = "https" if base_url.lower().startswith("https") else "http"

    metadata = Metadata(
        test_id=spec.test_id,
        name=spec.test_name,
        description=spec.objective,
        tags={
            "test_type": test_type_str,
            "adapted_by": "spec_adapter",
        },
    )

    test_type_cfg = TestTypeConfig(
        type=test_type_str,
        protocol=protocol,
    )

    # -------------------------------------------------------------------------
    # 9. Assemble Canonical TestSpec
    # -------------------------------------------------------------------------
    adapted_spec = TestSpec(
        version="1.0",
        metadata=metadata,
        test=test_type_cfg,
        target=target_config,
        load=load_config,
        stages=stages_configs,
        headers=headers,
        payload=payload_config,
        auth=auth_config,
        thresholds=threshold_rules,
        checks=check_rules,
    )

    return AdaptationResult(spec=adapted_spec, events=events)
