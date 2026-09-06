import re
from typing import Any, Dict, Optional
from performance_testing_ai.models.requirement import TestType, HttpMethod

def normalize_duration_seconds(duration: Any) -> float:
    """
    Normalizes duration expressions into total seconds.
    Examples:
        '10s', '10 seconds' -> 10.0
        '2m', '2 minutes', '5m' -> 120.0, 300.0
        '1h', '1 hour' -> 3600.0
        '500ms' -> 0.5
    """
    if duration is None:
        raise ValueError("Duration cannot be None")

    if isinstance(duration, (int, float)):
        return float(duration)

    d_str = str(duration).strip().lower()

    # Milliseconds
    m_ms = re.match(r"^([0-9.]+)\s*(ms|millis|millisecond|milliseconds)$", d_str)
    if m_ms:
        return float(m_ms.group(1)) / 1000.0

    # Seconds
    m_s = re.match(r"^([0-9.]+)\s*(s|sec|secs|second|seconds)$", d_str)
    if m_s:
        return float(m_s.group(1))

    # Minutes
    m_m = re.match(r"^([0-9.]+)\s*(m|min|mins|minute|minutes)$", d_str)
    if m_m:
        return float(m_m.group(1)) * 60.0

    # Hours
    m_h = re.match(r"^([0-9.]+)\s*(h|hr|hrs|hour|hours)$", d_str)
    if m_h:
        return float(m_h.group(1)) * 3600.0

    # Pure number
    if d_str.replace(".", "", 1).isdigit():
        return float(d_str)

    raise ValueError(f"Cannot parse duration into seconds: '{duration}'")

def normalize_latency_ms(latency: Any) -> float:
    """
    Normalizes latency expressions into milliseconds.
    Examples:
        '500ms', '500 ms', 500 -> 500.0
        '2s', '2 seconds', '1.5s' -> 2000.0, 1500.0
    """
    if latency is None:
        raise ValueError("Latency cannot be None")

    if isinstance(latency, (int, float)):
        return float(latency)

    l_str = str(latency).strip().lower()

    # Milliseconds
    m_ms = re.match(r"^([0-9.]+)\s*(ms|millis|millisecond|milliseconds)?$", l_str)
    if m_ms and m_ms.group(2):
        return float(m_ms.group(1))

    # Seconds
    m_s = re.match(r"^([0-9.]+)\s*(s|sec|secs|second|seconds)$", l_str)
    if m_s:
        return float(m_s.group(1)) * 1000.0

    # Pure number (default ms)
    if l_str.replace(".", "", 1).isdigit():
        return float(l_str)

    raise ValueError(f"Cannot parse latency into milliseconds: '{latency}'")

def normalize_error_rate(value: float, unit: str = "") -> Dict[str, Any]:
    """
    Normalizes and inspects error rate representation to detect percentage vs fraction discrepancies.
    
    Semantic Ground Truth:
    - 1% error rate means fraction 0.01 (1 failed out of 100).
    - If value=0.01 and unit="%", the literal interpretation is 0.01% (1 failed out of 10,000)!
    - If value=1.0 and unit="%", the literal interpretation is 1.0% (1 failed out of 100).
    - If value=0.01 and unit="" or unit="rate", the fraction is 0.01 (1%).
    """
    u_clean = (unit or "").strip().lower()
    val = float(value)

    # Inconsistency detection:
    # If an agent sets value=0.01 and unit="%", CLI prints "0.01%" which is 100x lower than 1%
    has_inconsistency = False
    inconsistency_reason: Optional[str] = None

    if u_clean == "%" and val < 0.1:
        has_inconsistency = True
        inconsistency_reason = (
            f"Possible fraction-percentage conflict: value={val} with unit='%' "
            f"formats to '{val}%' (fraction {val/100:.6f}), but likely meant {val*100:g}% (fraction {val})."
        )
        semantic_fraction = val  # Intended fraction
        semantic_percentage = val * 100.0
    elif u_clean == "%":
        semantic_fraction = val / 100.0
        semantic_percentage = val
    elif u_clean in ("rate", "fraction", ""):
        semantic_fraction = val
        semantic_percentage = val * 100.0
    else:
        semantic_fraction = val
        semantic_percentage = val * 100.0

    return {
        "raw_value": val,
        "raw_unit": unit,
        "semantic_fraction": semantic_fraction,
        "semantic_percentage": semantic_percentage,
        "display_string": f"{semantic_percentage:g}%",
        "has_inconsistency": has_inconsistency,
        "inconsistency_reason": inconsistency_reason,
    }

def normalize_test_type(test_type_input: Any) -> Optional[TestType]:
    """
    Normalizes natural language test type descriptions into TestType enum.
    """
    if isinstance(test_type_input, TestType):
        return test_type_input

    if not test_type_input:
        return None

    s = str(test_type_input).strip().lower()

    if any(k in s for k in ("stress", "breakpoint", "break point", "degradation", "limits", "push")):
        return TestType.STRESS
    if any(k in s for k in ("soak", "endurance", "continuous", "extended", "leak", "sustained")):
        return TestType.SOAK
    if any(k in s for k in ("baseline", "benchmark", "single user", "smoke", "sanity")):
        return TestType.BASELINE
    if any(k in s for k in ("load", "capacity", "expected peak", "traffic", "normal")):
        return TestType.LOAD

    return None

def normalize_http_method(method_input: Any) -> Optional[HttpMethod]:
    """Normalizes HTTP method string into HttpMethod enum."""
    if isinstance(method_input, HttpMethod):
        return method_input
    if not method_input:
        return None
    s = str(method_input).strip().upper()
    try:
        return HttpMethod(s)
    except ValueError:
        return None
