import re
from typing import Dict, Any, List
from app.models.test_spec import TestSpec, ThresholdRule


class SpecNormalizer:
    """
    Stage 8: Normalization & Canonical IR Generation.
    - Desugars shorthand representations (e.g. '5m' -> 300 seconds).
    - Guarantees uppercase HTTP methods.
    - Sanitizes base_url and endpoint paths.
    - Injects appropriate default headers (e.g. Content-Type for JSON payloads).
    - Unifies threshold representations into standard k6 format.
    """

    _DURATION_STR_RE = re.compile(r"^(\d+)\s*(s|m|h)?$", re.IGNORECASE)
    _THRESHOLD_PARSER_RE = re.compile(r"^(?:(p\(\s*\d+\s*\)|avg|min|max|med|rate|count)\s*)?([<>]=?|==)\s*(\d+(?:\.\d+)?(?:s|ms|m)?)$")

    @classmethod
    def parse_duration(cls, val: Any) -> int:
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            match = cls._DURATION_STR_RE.match(val.strip())
            if match:
                num = int(match.group(1))
                unit = (match.group(2) or "s").lower()
                if unit == "s":
                    return num
                elif unit == "m":
                    return num * 60
                elif unit == "h":
                    return num * 3600
        return 60

    @classmethod
    def normalize(cls, spec: TestSpec) -> Dict[str, Any]:
        spec_dict = spec.model_dump()

        # 1. Normalize Target
        base_url = spec.target.base_url.rstrip("/")
        endpoint = spec.target.endpoint.strip()
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        method = spec.target.method.strip().upper()

        spec_dict["target"]["base_url"] = base_url
        spec_dict["target"]["endpoint"] = endpoint
        spec_dict["target"]["method"] = method

        # 2. Normalize Headers
        headers = {k: v for k, v in spec.headers.items()}
        headers_lower = {k.lower(): k for k in headers}

        # Inject default Content-Type for JSON payloads
        if spec.payload.type == "json" and method in ("POST", "PUT", "PATCH"):
            if "content-type" not in headers_lower:
                headers["Content-Type"] = "application/json"

        # Inject default Accept header
        if "accept" not in headers_lower:
            headers["Accept"] = "*/*"

        # Inject Bearer Auth if auth type is bearer
        if spec.auth.type.lower() == "bearer" and spec.auth.token:
            if "authorization" not in headers_lower:
                token = spec.auth.token
                headers["Authorization"] = f"Bearer {token}"

        spec_dict["headers"] = headers

        # 3. Normalize Thresholds into unified k6 threshold mapping: { metric: [expr] }
        normalized_thresholds: Dict[str, List[str]] = {}

        if isinstance(spec.thresholds, list):
            for rule in spec.thresholds:
                if isinstance(rule, ThresholdRule):
                    metric = rule.metric
                    op = rule.operator
                    val = rule.value
                    if rule.percentile:
                        expr = f"p({rule.percentile}){op}{val}"
                    elif rule.aggregation:
                        expr = f"{rule.aggregation}{op}{val}"
                    else:
                        expr = f"{op}{val}"

                    if metric not in normalized_thresholds:
                        normalized_thresholds[metric] = []
                    normalized_thresholds[metric].append(expr)
                elif isinstance(rule, dict):
                    metric = rule.get("metric", "http_req_duration")
                    pct = rule.get("percentile")
                    agg = rule.get("aggregation")
                    op = rule.get("operator", "<")
                    val = rule.get("value", 500)
                    if pct:
                        expr = f"p({pct}){op}{val}"
                    elif agg:
                        expr = f"{agg}{op}{val}"
                    else:
                        expr = f"{op}{val}"

                    if metric not in normalized_thresholds:
                        normalized_thresholds[metric] = []
                    normalized_thresholds[metric].append(expr)

        elif isinstance(spec.thresholds, dict):
            for metric, expr in spec.thresholds.items():
                if isinstance(expr, list):
                    normalized_thresholds[metric] = [str(e) for e in expr]
                else:
                    normalized_thresholds[metric] = [str(expr)]

        # Default fallback threshold if none provided
        if not normalized_thresholds:
            normalized_thresholds = {
                "http_req_duration": ["p(95)<500"],
                "http_req_failed": ["rate<0.05"]
            }

        spec_dict["thresholds"] = normalized_thresholds

        # 4. Normalize Stages & Load
        if spec.stages:
            stage_list = []
            for s in spec.stages:
                stage_list.append({
                    "duration_seconds": s.duration_seconds,
                    "target_vus": s.target_vus
                })
            spec_dict["stages"] = stage_list
            spec_dict["load"]["duration_seconds"] = sum(s["duration_seconds"] for s in stage_list)
            spec_dict["load"]["target_vus"] = max(s["target_vus"] for s in stage_list)

        return spec_dict
