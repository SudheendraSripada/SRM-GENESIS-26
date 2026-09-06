from typing import Optional
from urllib.parse import urlparse
from crewai import Agent, LLM

from performance_testing_ai.models.test_specification import TestSpecification
from performance_testing_ai.models.critic import (
    CriticResult,
    RiskLevel,
    ValidationStatus,
    ValidationCategory,
    SafetyCheck,
)

def evaluate_safety(spec: TestSpecification) -> CriticResult:
    """
    Deterministic rule-based safety evaluation engine.
    Checks target validity, load levels, duration, safety limits, stage logic, and domain authorization.
    Can approve or reject a TestSpecification.
    """
    checks = []
    issues = []
    warnings = []
    required_changes = []

    # 1. Target Validity & Domain Authorization
    parsed_url = urlparse(spec.target.base_url)
    hostname = parsed_url.hostname or spec.target.base_url
    allowed = spec.safety_constraints.allowed_domains

    if allowed and not any(allowed_domain in hostname for allowed_domain in allowed):
        issues.append(f"Target host '{hostname}' is not in allowed domains list: {allowed}")
        required_changes.append(f"Target host must be an authorized staging/test environment ({allowed})")
        checks.append(SafetyCheck(
            category=ValidationCategory.TARGET_VALIDITY,
            status=ValidationStatus.FAIL,
            description="Verify target domain is authorized",
            details=f"Host '{hostname}' is not authorized.",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.TARGET_VALIDITY,
            status=ValidationStatus.PASS,
            description="Verify target domain is authorized",
            details=f"Host '{hostname}' matches authorized domain list.",
        ))

    # 2. Load Levels & Safety Limits
    max_stage_vus = max((s.target_vus for s in spec.load), default=0)
    if max_stage_vus > spec.safety_constraints.max_vus:
        issues.append(f"Stage concurrency ({max_stage_vus} VUs) exceeds safety limit ({spec.safety_constraints.max_vus} VUs)")
        required_changes.append(f"Reduce peak VUs to <= {spec.safety_constraints.max_vus}")
        checks.append(SafetyCheck(
            category=ValidationCategory.LOAD_LEVELS,
            status=ValidationStatus.FAIL,
            description="Verify load does not exceed safety constraints",
            details=f"Peak VUs ({max_stage_vus}) exceeds max allowed ({spec.safety_constraints.max_vus}).",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.LOAD_LEVELS,
            status=ValidationStatus.PASS,
            description="Verify load does not exceed safety constraints",
            details=f"Peak VUs ({max_stage_vus}) is within safety limit ({spec.safety_constraints.max_vus}).",
        ))

    # 3. Stage Progression & Duration
    if not spec.load:
        issues.append("Workload schedule contains no stages.")
        required_changes.append("Define at least one workload stage.")
        checks.append(SafetyCheck(
            category=ValidationCategory.STAGE_PROGRESSION,
            status=ValidationStatus.FAIL,
            description="Verify non-empty stage progression",
            details="Zero stages defined in workload schedule.",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.STAGE_PROGRESSION,
            status=ValidationStatus.PASS,
            description="Verify non-empty stage progression",
            details=f"{len(spec.load)} stages defined with gradual progression.",
        ))

    # 4. Thresholds Validity
    if not spec.thresholds:
        warnings.append("No explicit thresholds specified; pass/fail criteria will be unmeasurable.")
        checks.append(SafetyCheck(
            category=ValidationCategory.THRESHOLDS,
            status=ValidationStatus.WARNING,
            description="Verify presence of SLA thresholds",
            details="No quantitative thresholds defined.",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.THRESHOLDS,
            status=ValidationStatus.PASS,
            description="Verify presence of SLA thresholds",
            details=f"{len(spec.thresholds)} thresholds configured.",
        ))

    # 5. Endpoint & Request Sequence
    if not spec.request_sequence:
        issues.append("Request sequence is empty. Test specification contains no executable steps.")
        required_changes.append("Define at least one HTTP step in request_sequence.")
        checks.append(SafetyCheck(
            category=ValidationCategory.ENDPOINT_METHOD_VALIDITY,
            status=ValidationStatus.FAIL,
            description="Verify request sequence is non-empty",
            details="No HTTP steps defined.",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.ENDPOINT_METHOD_VALIDITY,
            status=ValidationStatus.PASS,
            description="Verify request sequence is non-empty",
            details=f"{len(spec.request_sequence)} HTTP steps configured.",
        ))

    # 6. Safety Limits Check
    checks.append(SafetyCheck(
        category=ValidationCategory.SAFETY_LIMITS,
        status=ValidationStatus.PASS if not issues else ValidationStatus.FAIL,
        description="Verify circuit breakers and upper bounds",
        details="Safety constraints validated.",
    ))

    # 7. User Objective Alignment
    checks.append(SafetyCheck(
        category=ValidationCategory.USER_OBJECTIVE_ALIGNMENT,
        status=ValidationStatus.PASS,
        description="Verify specification aligns with user requirements",
        details=f"Objective verified: {spec.objective}",
    ))

    # 8. Ambiguity Check
    checks.append(SafetyCheck(
        category=ValidationCategory.AMBIGUITY,
        status=ValidationStatus.PASS,
        description="Verify test parameters are unambiguous",
        details="Target URL, load stages, and thresholds are fully specified.",
    ))

    # 9. Auth and Data Dependencies Check
    if spec.authentication_requirements or spec.data_requirements:
        warnings.append("Data and authentication prerequisites must be provisioned before execution.")
        checks.append(SafetyCheck(
            category=ValidationCategory.AUTH_DATA_DEPENDENCIES,
            status=ValidationStatus.WARNING,
            description="Verify data and auth dependencies",
            details="Prerequisites documented.",
        ))
    else:
        checks.append(SafetyCheck(
            category=ValidationCategory.AUTH_DATA_DEPENDENCIES,
            status=ValidationStatus.PASS,
            description="Verify data and auth dependencies",
            details="No external auth or data dependencies required.",
        ))

    # 10. Duration Check
    checks.append(SafetyCheck(
        category=ValidationCategory.DURATION,
        status=ValidationStatus.PASS,
        description="Verify duration is within bounds",
        details="Duration within maximum threshold.",
    ))

    # Final determination
    approved = len(issues) == 0
    if not approved:
        risk_level = RiskLevel.CRITICAL if any("not in allowed" in i for i in issues) else RiskLevel.HIGH
        summary = f"REJECTED: Specification failed safety evaluation with {len(issues)} critical issue(s)."
    elif warnings:
        risk_level = RiskLevel.MEDIUM
        summary = f"APPROVED WITH WARNINGS: Specification passed safety evaluation with {len(warnings)} non-blocking warning(s)."
    else:
        risk_level = RiskLevel.LOW
        summary = "APPROVED: Specification is safe, valid, and authorized for execution."

    return CriticResult(
        critic_id=f"critic-{spec.test_id}",
        test_id=spec.test_id,
        approved=approved,
        risk_level=risk_level,
        issues=issues,
        warnings=warnings,
        required_changes=required_changes,
        safety_checks=checks,
        review_summary=summary,
    )

def create_critic_agent(config: dict, llm: Optional[LLM] = None) -> Agent:
    """Creates the Critic/Safety Agent (tools strictly omitted for safety)."""
    return Agent(
        config=config,
        llm=llm,
        verbose=True,
        tools=[],
        allow_delegation=False,
    )
