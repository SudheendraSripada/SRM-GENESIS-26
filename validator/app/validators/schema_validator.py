from typing import Tuple, Optional, List, Dict, Any
from pydantic import ValidationError
from app.models.test_spec import TestSpec
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class SchemaValidator:
    """
    Stage 2: Schema Validation & Type Invariant Checking using Pydantic v2.
    - Validates structural completeness and types.
    - Maps Pydantic loc tuples to clean dot-separated JSON paths.
    - Distinguishes missing fields vs type mismatches.
    """

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Tuple[Optional[TestSpec], List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        try:
            spec = TestSpec.model_validate(data)
            return spec, errors, warnings
        except ValidationError as val_err:
            for err in val_err.errors():
                loc_path = ".".join(str(elem) for elem in err["loc"])
                err_type = err["type"]
                msg = err["msg"]

                if "missing" in err_type:
                    code = ErrorCatalog.SCHEMA_MISSING_FIELD
                    expected = "non-null required value"
                    received = "undefined"
                    repair_hint = f"Add missing required field '{loc_path}'."
                else:
                    code = ErrorCatalog.SCHEMA_INVALID_TYPE
                    expected = err_type.replace("_type", "").replace("_parsing", "")
                    received = str(err.get("input", "unknown"))
                    repair_hint = f"Update '{loc_path}' to match expected schema type ({expected})."

                errors.append(
                    ValidationErrorItem(
                        code=code,
                        stage=StageName.SCHEMA,
                        path=loc_path,
                        message=msg,
                        severity=Severity.ERROR,
                        expected=expected,
                        received=received,
                        repair_hint=repair_hint
                    )
                )

            return None, errors, warnings
