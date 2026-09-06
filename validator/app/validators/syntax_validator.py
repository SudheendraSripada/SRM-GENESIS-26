import json
import re
from typing import Tuple, Optional, Any, List
from app.models.validation_result import (
    ValidationErrorItem,
    Severity,
    StageName,
    ErrorCatalog,
)


class SyntaxValidator:
    """
    Stage 1: O(N) Single-Pass Syntax & Structural Pre-check.
    - Strips markdown code fences if present.
    - Accurately tracks line and column offsets of parse failures.
    - Detects trailing commas, unmatched braces, and unclosed quotes.
    """

    _MARKDOWN_CODEBLOCK_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)
    _TRAILING_COMMA_RE = re.compile(r",\s*([\]\}])")

    @classmethod
    def validate(cls, raw_input: Any) -> Tuple[Optional[dict], List[ValidationErrorItem], List[ValidationErrorItem]]:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        if raw_input is None:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SYNTAX_EMPTY_PAYLOAD,
                    stage=StageName.SYNTAX,
                    path="$",
                    message="Received null or empty input",
                    severity=Severity.CRITICAL,
                    expected="valid JSON object string or dictionary",
                    received="null",
                    repair_hint="Provide a valid JSON packet with TestSpec fields."
                )
            )
            return None, errors, warnings

        if isinstance(raw_input, dict):
            return raw_input, errors, warnings

        if not isinstance(raw_input, str):
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SYNTAX_INVALID_JSON,
                    stage=StageName.SYNTAX,
                    path="$",
                    message=f"Input must be a JSON string or dict, got {type(raw_input).__name__}",
                    severity=Severity.CRITICAL,
                    expected="string or dict",
                    received=type(raw_input).__name__,
                    repair_hint="Serialize input packet to a JSON string."
                )
            )
            return None, errors, warnings

        cleaned_text = raw_input.strip()
        if not cleaned_text:
            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SYNTAX_EMPTY_PAYLOAD,
                    stage=StageName.SYNTAX,
                    path="$",
                    message="JSON string is empty or contains only whitespace",
                    severity=Severity.CRITICAL,
                    expected="non-empty JSON string",
                    received="empty string",
                    repair_hint="Provide non-empty TestSpec JSON."
                )
            )
            return None, errors, warnings

        # Check for Markdown fencing
        match = cls._MARKDOWN_CODEBLOCK_RE.match(cleaned_text)
        if match:
            cleaned_text = match.group(1).strip()
            warnings.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SYNTAX_MARKDOWN_BLOCK,
                    stage=StageName.SYNTAX,
                    path="$",
                    message="AI output was wrapped in Markdown code fences; stripped automatically",
                    severity=Severity.INFO,
                    repair_hint="Ensure AI returns raw JSON without markdown ```json blocks."
                )
            )

        # Fast O(N) JSON parse
        try:
            parsed = json.loads(cleaned_text)
            if not isinstance(parsed, dict):
                errors.append(
                    ValidationErrorItem(
                        code=ErrorCatalog.SYNTAX_INVALID_JSON,
                        stage=StageName.SYNTAX,
                        path="$",
                        message=f"Root of TestSpec must be a JSON object, got {type(parsed).__name__}",
                        severity=Severity.CRITICAL,
                        expected="JSON object (dict)",
                        received=type(parsed).__name__,
                        repair_hint="Enclose TestSpec fields in curly braces {}."
                    )
                )
                return None, errors, warnings
            return parsed, errors, warnings

        except json.JSONDecodeError as exc:
            # Diagnose specific common errors
            line = exc.lineno
            col = exc.colno
            pos = exc.pos
            msg = exc.msg

            repair_hint = f"Syntax error at line {line}, column {col}: {msg}"
            # Check trailing comma near pos
            snippet = cleaned_text[max(0, pos - 20): min(len(cleaned_text), pos + 20)]
            if cls._TRAILING_COMMA_RE.search(snippet):
                repair_hint = f"Trailing comma detected near line {line}, col {col}. Remove trailing commas before closing braces/brackets."

            errors.append(
                ValidationErrorItem(
                    code=ErrorCatalog.SYNTAX_INVALID_JSON,
                    stage=StageName.SYNTAX,
                    path=f"line:{line},col:{col}",
                    message=f"Malformed JSON syntax: {msg}",
                    severity=Severity.CRITICAL,
                    expected="Valid RFC 8259 JSON",
                    received=f"Error at character offset {pos}",
                    repair_hint=repair_hint
                )
            )
            return None, errors, warnings
