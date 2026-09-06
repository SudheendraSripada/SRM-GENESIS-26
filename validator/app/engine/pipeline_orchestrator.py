from typing import Any, Optional, Dict, List
from app.models.safety_policy import SafetyPolicy
from app.models.validation_result import (
    ValidationResult,
    ValidationErrorItem,
    StageName,
    StageStatus,
    PipelineStatus,
)
from app.validators.syntax_validator import SyntaxValidator
from app.validators.schema_validator import SchemaValidator
from app.validators.constraint_validator import ConstraintValidator
from app.validators.semantic_validator import SemanticValidator
from app.validators.cross_field_validator import CrossFieldValidator
from app.validators.safety_validator import SafetyValidator
from app.validators.k6_compat_validator import K6CompatibilityValidator
from app.normalizer.spec_normalizer import SpecNormalizer
from app.compiler.k6_compiler import K6Compiler


class PipelineOrchestrator:
    """
    Main Orchestrator for the 8-Stage Progressive Verification & Compilation Pipeline.
    Executes stages strictly from lowest computational complexity to highest,
    short-circuiting early on fatal syntax or structural failures.
    """

    def __init__(self, policy: Optional[SafetyPolicy] = None):
        self.policy = policy or SafetyPolicy()

    def run(self, raw_input: Any, auto_compile: bool = True) -> ValidationResult:
        all_errors: List[ValidationErrorItem] = []
        all_warnings: List[ValidationErrorItem] = []

        stages_status: Dict[str, StageStatus] = {
            StageName.SYNTAX.value: StageStatus.SKIPPED,
            StageName.SCHEMA.value: StageStatus.SKIPPED,
            StageName.CONSTRAINTS.value: StageStatus.SKIPPED,
            StageName.SEMANTIC.value: StageStatus.SKIPPED,
            StageName.CROSS_FIELD.value: StageStatus.SKIPPED,
            StageName.SAFETY.value: StageStatus.SKIPPED,
            StageName.K6_COMPATIBILITY.value: StageStatus.SKIPPED,
            StageName.NORMALIZATION.value: StageStatus.SKIPPED,
            StageName.COMPILATION.value: StageStatus.SKIPPED,
        }

        # -------------------------------------------------------------
        # Stage 1: JSON Syntax Validation (O(N))
        # -------------------------------------------------------------
        parsed_dict, syn_errs, syn_warns = SyntaxValidator.validate(raw_input)
        all_warnings.extend(syn_warns)

        if syn_errs:
            stages_status[StageName.SYNTAX.value] = StageStatus.FAIL
            all_errors.extend(syn_errs)
            return ValidationResult(
                status=PipelineStatus.REJECTED,
                validation_score=0,
                stages=stages_status,
                errors=all_errors,
                warnings=all_warnings,
            )
        stages_status[StageName.SYNTAX.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 2: Schema Validation (Pydantic Core)
        # -------------------------------------------------------------
        spec, sch_errs, sch_warns = SchemaValidator.validate(parsed_dict)
        all_warnings.extend(sch_warns)

        if sch_errs or spec is None:
            stages_status[StageName.SCHEMA.value] = StageStatus.FAIL
            all_errors.extend(sch_errs)
            return ValidationResult(
                status=PipelineStatus.REJECTED,
                validation_score=15,
                stages=stages_status,
                errors=all_errors,
                warnings=all_warnings,
            )
        stages_status[StageName.SCHEMA.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 3: Primitive & Field-Level Constraints
        # -------------------------------------------------------------
        con_errs, con_warns = ConstraintValidator.validate(spec)
        all_warnings.extend(con_warns)
        if con_errs:
            stages_status[StageName.CONSTRAINTS.value] = StageStatus.FAIL
            all_errors.extend(con_errs)
        else:
            stages_status[StageName.CONSTRAINTS.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 4: Test-Type Semantic Profile
        # -------------------------------------------------------------
        sem_errs, sem_warns = SemanticValidator.validate(spec)
        all_warnings.extend(sem_warns)
        if sem_errs:
            stages_status[StageName.SEMANTIC.value] = StageStatus.FAIL
            all_errors.extend(sem_errs)
        else:
            stages_status[StageName.SEMANTIC.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 5: Cross-Field Invariants & Dependencies
        # -------------------------------------------------------------
        cro_errs, cro_warns = CrossFieldValidator.validate(spec)
        all_warnings.extend(cro_warns)
        if cro_errs:
            stages_status[StageName.CROSS_FIELD.value] = StageStatus.FAIL
            all_errors.extend(cro_errs)
        else:
            stages_status[StageName.CROSS_FIELD.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 6: Safety & Policy Gate (Hard Firewall)
        # -------------------------------------------------------------
        saf_errs, saf_warns = SafetyValidator.validate(spec, self.policy)
        all_warnings.extend(saf_warns)
        if saf_errs:
            stages_status[StageName.SAFETY.value] = StageStatus.FAIL
            all_errors.extend(saf_errs)
        else:
            stages_status[StageName.SAFETY.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 7: k6 Compatibility Gate
        # -------------------------------------------------------------
        k6_errs, k6_warns = K6CompatibilityValidator.validate(spec)
        all_warnings.extend(k6_warns)
        if k6_errs:
            stages_status[StageName.K6_COMPATIBILITY.value] = StageStatus.FAIL
            all_errors.extend(k6_errs)
        else:
            stages_status[StageName.K6_COMPATIBILITY.value] = StageStatus.PASS

        # Determine overall validity before normalization/compilation
        if all_errors:
            passed_stages_count = sum(1 for s in stages_status.values() if s == StageStatus.PASS)
            score = max(5, int((passed_stages_count / 7.0) * 80) - (len(all_errors) * 10))
            return ValidationResult(
                status=PipelineStatus.REJECTED,
                validation_score=score,
                stages=stages_status,
                errors=all_errors,
                warnings=all_warnings,
            )

        # -------------------------------------------------------------
        # Stage 8: Normalization & Canonical IR Generation
        # -------------------------------------------------------------
        normalized_spec = SpecNormalizer.normalize(spec)
        stages_status[StageName.NORMALIZATION.value] = StageStatus.PASS

        # -------------------------------------------------------------
        # Stage 9: Deterministic k6 Script Compiler
        # -------------------------------------------------------------
        compiled_script = None
        if auto_compile:
            compiled_script = K6Compiler.compile(normalized_spec)
            stages_status[StageName.COMPILATION.value] = StageStatus.PASS

        # Calculate final high score
        score = max(80, 100 - (len(all_warnings) * 4))

        return ValidationResult(
            status=PipelineStatus.VALID,
            validation_score=score,
            stages=stages_status,
            errors=[],
            warnings=all_warnings,
            normalized_spec=normalized_spec,
            compiled_k6_script=compiled_script,
        )
