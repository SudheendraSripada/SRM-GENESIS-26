import ipaddress
from typing import List, Tuple
from urllib.parse import urlparse
from app.models.test_spec import TestSpec
from app.models.safety_policy import SafetyPolicy
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class SafetyValidator:
    """
    Stage 6: Safety & Policy Gate (Hard Security Firewall).
    - Hard caps on VUs (e.g. <= 1000).
    - Hard caps on total execution duration (e.g. <= 1800s).
    - Hard caps on stage count (e.g. <= 20).
    - SSRF prevention against cloud metadata services (169.254.169.254) and reserved CIDRs.
    - Strict target URL domain allowlist verification.
    """

    @classmethod
    def validate(cls, spec: TestSpec, policy: SafetyPolicy) -> Tuple[List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        # 1. VU Caps
        if spec.load.start_vus > policy.max_vus:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SAFETY_MAX_VUS_EXCEEDED,
                    stage=StageName.SAFETY,
                    path="load.start_vus",
                    message=f"Requested start_vus ({spec.load.start_vus}) exceeds maximum platform policy ({policy.max_vus})",
                    severity=Severity.CRITICAL,
                    expected=f"<= {policy.max_vus}",
                    received=str(spec.load.start_vus),
                    repair_hint=f"Reduce 'load.start_vus' to at most {policy.max_vus}."
                )
            )

        if spec.load.target_vus > policy.max_vus:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SAFETY_MAX_VUS_EXCEEDED,
                    stage=StageName.SAFETY,
                    path="load.target_vus",
                    message=f"Requested target_vus ({spec.load.target_vus}) exceeds maximum platform policy ({policy.max_vus})",
                    severity=Severity.CRITICAL,
                    expected=f"<= {policy.max_vus}",
                    received=str(spec.load.target_vus),
                    repair_hint=f"Reduce 'load.target_vus' to at most {policy.max_vus}."
                )
            )

        for idx, stage in enumerate(spec.stages):
            if stage.target_vus > policy.max_vus:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SAFETY_MAX_VUS_EXCEEDED,
                        stage=StageName.SAFETY,
                        path=f"stages[{idx}].target_vus",
                        message=f"Stage {idx} target_vus ({stage.target_vus}) exceeds policy ceiling ({policy.max_vus})",
                        severity=Severity.CRITICAL,
                        expected=f"<= {policy.max_vus}",
                        received=str(stage.target_vus),
                        repair_hint=f"Clamp stage {idx} target_vus to {policy.max_vus} or lower."
                    )
                )

        # 2. Duration Caps
        if spec.load.duration_seconds > policy.max_duration_seconds:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SAFETY_MAX_DURATION_EXCEEDED,
                    stage=StageName.SAFETY,
                    path="load.duration_seconds",
                    message=f"Requested duration ({spec.load.duration_seconds}s) exceeds policy ceiling ({policy.max_duration_seconds}s)",
                    severity=Severity.CRITICAL,
                    expected=f"<= {policy.max_duration_seconds}s",
                    received=f"{spec.load.duration_seconds}s",
                    repair_hint=f"Limit test duration to at most {policy.max_duration_seconds} seconds."
                )
            )

        # 3. Stage count cap
        if len(spec.stages) > policy.max_stages:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SAFETY_MAX_STAGES_EXCEEDED,
                    stage=StageName.SAFETY,
                    path="stages",
                    message=f"Number of stages ({len(spec.stages)}) exceeds limit ({policy.max_stages})",
                    severity=Severity.CRITICAL,
                    expected=f"<= {policy.max_stages}",
                    received=str(len(spec.stages)),
                    repair_hint=f"Consolidate stages to a maximum of {policy.max_stages} steps."
                )
            )

        # 4. Target URL / SSRF & Allowlist
        parsed = urlparse(spec.target.base_url)
        hostname = (parsed.hostname or "").lower()

        # Check IP / SSRF
        try:
            ip = ipaddress.ip_address(hostname)
            # Check blocked CIDRs
            for cidr_str in policy.blocked_cidrs:
                network = ipaddress.ip_network(cidr_str)
                if ip in network:
                    errors.append(
                        ValidationErrorItem(
                            code=ErrorCatalog.SAFETY_SSRF_PROHIBITED_IP,
                            stage=StageName.SAFETY,
                            path="target.base_url",
                            message=f"Target IP {hostname} falls within prohibited CIDR range {cidr_str}",
                            severity=Severity.CRITICAL,
                            expected="Routable public or permitted staging address",
                            received=hostname,
                            repair_hint="Do not target cloud metadata (169.254.169.254) or reserved addresses."
                        )
                    )
                    break

            if ip.is_loopback and not policy.allow_localhost:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SAFETY_TARGET_NOT_ALLOWED,
                        stage=StageName.SAFETY,
                        path="target.base_url",
                        message="Localhost / loopback target prohibited by policy in this environment",
                        severity=Severity.CRITICAL,
                        expected="Allowed external or staging target",
                        received=hostname,
                        repair_hint="Target a permitted staging endpoint."
                    )
                )
        except ValueError:
            # Not a raw IP; it's a domain name
            pass

        # Check domain against allowed targets if allowed_targets is non-empty
        if policy.allowed_targets:
            target_str = spec.target.base_url.lower().rstrip("/")
            is_allowed = False
            for allowed in policy.allowed_targets:
                allowed_norm = allowed.lower().rstrip("/")
                if target_str == allowed_norm or target_str.startswith(allowed_norm) or hostname == allowed_norm:
                    is_allowed = True
                    break
                # Handle domain matching like example.com
                if hostname.endswith(allowed_norm) or allowed_norm.endswith(hostname):
                    is_allowed = True
                    break

            if not is_allowed:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SAFETY_TARGET_NOT_ALLOWED,
                        stage=StageName.SAFETY,
                        path="target.base_url",
                        message=f"Target host '{spec.target.base_url}' is not in the approved target allowlist",
                        severity=Severity.CRITICAL,
                        expected=f"One of {policy.allowed_targets}",
                        received=spec.target.base_url,
                        repair_hint="Choose an approved target URL from the platform allowlist."
                    )
                )

        return errors, warnings
