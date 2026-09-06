from typing import List, Tuple
from app.models.test_spec import TestSpec
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class SemanticValidator:
    """
    Stage 4: Test-Type Semantic Validator.
    - Stress: Monotonically increasing or ramp-and-hold load curve.
    - Soak: Sustained duration with stable plateau.
    - Spike: Sharp peak ratio with cooldown phase.
    - Baseline: Moderate, steady load without abrupt surges.
    """

    @classmethod
    def validate(cls, spec: TestSpec) -> Tuple[List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        test_type = spec.test.type.lower()
        stages = spec.stages

        if not stages:
            # If no stages, semantic checks relate only to load configuration
            if test_type == "stress" and spec.load.target_vus <= spec.load.start_vus:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SEMANTIC_STRESS_NON_INCREASING,
                        stage=StageName.SEMANTIC,
                        path="load.target_vus",
                        message=f"Stress test requires target_vus ({spec.load.target_vus}) > start_vus ({spec.load.start_vus})",
                        severity=Severity.ERROR,
                        expected=f"> {spec.load.start_vus}",
                        received=str(spec.load.target_vus),
                        repair_hint="Increase target_vus or decrease start_vus so load intensifies."
                    )
                )
            return errors, warnings

        # Semantic validation when stages are defined
        vus_sequence = [spec.load.start_vus] + [s.target_vus for s in stages]

        if test_type == "stress":
            # For a stress test, the load must increase across stages to find breaking threshold
            peak_vu = max(vus_sequence)
            if peak_vu <= spec.load.start_vus and len(vus_sequence) > 1:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SEMANTIC_STRESS_NON_INCREASING,
                        stage=StageName.SEMANTIC,
                        path="stages",
                        message="Stress test stages must increase beyond initial start_vus",
                        severity=Severity.ERROR,
                        expected=f"Peak stage VUs > {spec.load.start_vus}",
                        received=f"Peak stage VUs = {peak_vu}",
                        repair_hint="Configure stages with increasing target_vus values."
                    )
                )

            # Check if stages are monotonically non-decreasing until peak
            peak_index = vus_sequence.index(peak_vu)
            # Up to peak_index, load should not drop
            for i in range(1, peak_index + 1):
                if vus_sequence[i] < vus_sequence[i - 1]:
                    errors.append(
                        ValidationErrorItem(
                            code=ErrorCatalog.SEMANTIC_STRESS_NON_INCREASING,
                            stage=StageName.SEMANTIC,
                            path=f"stages[{i - 1}].target_vus",
                            message=f"Stress test stage {i - 1} drops from {vus_sequence[i - 1]} to {vus_sequence[i]} VUs before peak",
                            severity=Severity.ERROR,
                            expected=f">= {vus_sequence[i - 1]} VUs",
                            received=f"{vus_sequence[i]} VUs",
                            repair_hint="Ensure stress test stages ramp up progressively (e.g. 10 -> 50 -> 100)."
                        )
                    )
                    break

        elif test_type == "soak":
            # Soak requires sustained duration (e.g. >= 300s in test env)
            total_stage_duration = sum(s.duration_seconds for s in stages)
            if total_stage_duration < 300 and spec.load.duration_seconds < 300:
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SEMANTIC_SOAK_TOO_SHORT,
                        stage=StageName.SEMANTIC,
                        path="load.duration_seconds",
                        message=f"Soak tests require sustained load (minimum 300s, received {total_stage_duration}s)",
                        severity=Severity.ERROR,
                        expected=">= 300 seconds",
                        received=f"{total_stage_duration} seconds",
                        repair_hint="Increase stage durations to sustain load for a soak endurance test."
                    )
                )

        elif test_type == "spike":
            # Spike test requires a significant peak relative to baseline
            baseline_vus = vus_sequence[0] or 1
            peak_vus = max(vus_sequence)
            if peak_vus < baseline_vus * 2 and peak_vus < 50:
                warnings.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SEMANTIC_SPIKE_INSUFFICIENT_PEAK,
                        stage=StageName.SEMANTIC,
                        path="stages",
                        message=f"Spike test peak ({peak_vus} VUs) is not significantly higher than baseline ({baseline_vus} VUs)",
                        severity=Severity.WARNING,
                        expected=f"Peak >= {baseline_vus * 2} VUs",
                        received=f"Peak = {peak_vus} VUs",
                        repair_hint="Consider a higher peak in the spike stage to observe surge response."
                    )
                )

        elif test_type == "baseline":
            # Baseline test should have low/moderate load
            peak_vus = max(vus_sequence)
            if peak_vus > 50:
                warnings.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SEMANTIC_BASELINE_UNSTABLE,
                        stage=StageName.SEMANTIC,
                        path="load.target_vus",
                        message=f"Baseline test has high load ({peak_vus} VUs). Baselines typically evaluate low concurrency (5-20 VUs)",
                        severity=Severity.WARNING,
                        expected="<= 50 VUs",
                        received=f"{peak_vus} VUs",
                        repair_hint="Lower target_vus to establish a clean reference baseline."
                    )
                )

        return errors, warnings
