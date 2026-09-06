import copy
from typing import Dict, Any, List, Tuple
from app.models.validation_result import ValidationErrorItem, ErrorCatalog
from app.models.safety_policy import SafetyPolicy


class RepairEngine:
    """
    Stage 11: Deterministic Constraint-Guided Auto-Repair Engine.
    - Inspects detected validation errors.
    - Proposes exact algorithmic fixes for structural, semantic, and safety violations.
    - Ensures repaired spec remains compliant with the Canonical JSON Contract.
    """

    @classmethod
    def attempt_repair(
        cls,
        raw_dict: Dict[str, Any],
        errors: List[ValidationErrorItem],
        policy: SafetyPolicy
    ) -> Tuple[Dict[str, Any], List[str]]:
        repaired = copy.deepcopy(raw_dict)
        applied_fixes: List[str] = []

        for err in errors:
            code = err.code

            # Fix 1: Duration Mismatch
            if code == ErrorCatalog.CROSS_FIELD_DURATION_MISMATCH:
                stages = repaired.get("stages", [])
                if stages:
                    stage_sum = sum(s.get("duration_seconds", 0) for s in stages)
                    if "load" in repaired:
                        repaired["load"]["duration_seconds"] = stage_sum
                        applied_fixes.append(
                            f"Synchronized load.duration_seconds from {repaired['load'].get('duration_seconds')} to {stage_sum}s (matching stage sum)"
                        )

            # Fix 2: Stress Load Non-Increasing
            elif code == ErrorCatalog.SEMANTIC_STRESS_NON_INCREASING:
                stages = repaired.get("stages", [])
                if stages:
                    current_vu = repaired.get("load", {}).get("start_vus", 5)
                    for idx, s in enumerate(stages):
                        target_vu = s.get("target_vus", current_vu)
                        if target_vu < current_vu:
                            s["target_vus"] = current_vu + 20
                            applied_fixes.append(
                                f"Adjusted stage {idx} target_vus from {target_vu} to {s['target_vus']} to ensure monotonic ramp"
                            )
                        current_vu = s["target_vus"]
                    if "load" in repaired and repaired["load"].get("target_vus", 0) < current_vu:
                        repaired["load"]["target_vus"] = current_vu
                        applied_fixes.append(f"Updated load.target_vus to peak stage VU ({current_vu})")

            # Fix 3: Method uppercase or invalid method
            elif code == ErrorCatalog.CONSTRAINT_INVALID_METHOD:
                if "target" in repaired and "method" in repaired["target"]:
                    curr_method = str(repaired["target"]["method"]).strip().upper()
                    if curr_method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                        repaired["target"]["method"] = curr_method
                        applied_fixes.append(f"Uppercased HTTP method to {curr_method}")
                    else:
                        repaired["target"]["method"] = "POST"
                        applied_fixes.append(f"Replaced unsupported method '{curr_method}' with POST")

            # Fix 4: Negative VUs / Range
            elif code == ErrorCatalog.CONSTRAINT_VUS_RANGE:
                if "load" in repaired:
                    if repaired["load"].get("start_vus", 0) < 0:
                        repaired["load"]["start_vus"] = 1
                        applied_fixes.append("Clamped negative load.start_vus to 1")
                    if repaired["load"].get("target_vus", 0) <= 0:
                        repaired["load"]["target_vus"] = 10
                        applied_fixes.append("Reset non-positive load.target_vus to 10")

            # Fix 5: GET with body
            elif code == ErrorCatalog.CROSS_FIELD_GET_WITH_BODY:
                if "target" in repaired and repaired["target"].get("method", "").upper() in ("GET", "HEAD"):
                    # Switch to POST if meaningful body exists, otherwise clear body
                    body = repaired.get("payload", {}).get("body")
                    if body:
                        repaired["target"]["method"] = "POST"
                        applied_fixes.append("Switched method from GET to POST because a non-empty payload body is defined")
                    else:
                        if "payload" in repaired:
                            repaired["payload"]["body"] = None
                            applied_fixes.append("Cleared empty body for GET request")

            # Fix 6: Safety VU Exceeded
            elif code == ErrorCatalog.SAFETY_MAX_VUS_EXCEEDED:
                if "load" in repaired:
                    if repaired["load"].get("start_vus", 0) > policy.max_vus:
                        repaired["load"]["start_vus"] = policy.max_vus // 2
                        applied_fixes.append(f"Clamped start_vus to {policy.max_vus // 2}")
                    if repaired["load"].get("target_vus", 0) > policy.max_vus:
                        repaired["load"]["target_vus"] = policy.max_vus
                        applied_fixes.append(f"Clamped target_vus to policy ceiling ({policy.max_vus})")

                for idx, s in enumerate(repaired.get("stages", [])):
                    if s.get("target_vus", 0) > policy.max_vus:
                        s["target_vus"] = policy.max_vus
                        applied_fixes.append(f"Clamped stage {idx} target_vus to {policy.max_vus}")

            # Fix 7: Safety Duration Exceeded
            elif code == ErrorCatalog.SAFETY_MAX_DURATION_EXCEEDED:
                if "load" in repaired:
                    repaired["load"]["duration_seconds"] = policy.max_duration_seconds
                    applied_fixes.append(f"Capped total test duration to {policy.max_duration_seconds}s")
                stages = repaired.get("stages", [])
                if stages:
                    # Scale down stage durations proportionally
                    curr_sum = sum(s.get("duration_seconds", 0) for s in stages) or 1
                    factor = policy.max_duration_seconds / curr_sum
                    for s in stages:
                        s["duration_seconds"] = max(1, int(s.get("duration_seconds", 0) * factor))
                    applied_fixes.append(f"Proportionally scaled down stage durations to fit {policy.max_duration_seconds}s limit")

            # Fix 8: Start VUs > Target VUs
            elif code == ErrorCatalog.CROSS_FIELD_START_GREATER_THAN_TARGET:
                if "load" in repaired:
                    s_vus = repaired["load"].get("start_vus", 10)
                    t_vus = repaired["load"].get("target_vus", 100)
                    repaired["load"]["start_vus"] = min(s_vus, t_vus)
                    repaired["load"]["target_vus"] = max(s_vus, t_vus)
                    applied_fixes.append(f"Swapped start_vus ({s_vus}) and target_vus ({t_vus}) so start <= target")

        return repaired, applied_fixes
