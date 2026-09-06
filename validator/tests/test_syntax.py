import pytest
from app.validators.syntax_validator import SyntaxValidator
from app.models.validation_result import ErrorCatalog


def test_valid_json_string():
    raw = '{"target": {"base_url": "https://example.com"}}'
    parsed, errs, warns = SyntaxValidator.validate(raw)
    assert errs == []
    assert parsed["target"]["base_url"] == "https://example.com"


def test_markdown_fence_stripping():
    raw = """```json
{
  "target": {"base_url": "https://example.com"}
}
```"""
    parsed, errs, warns = SyntaxValidator.validate(raw)
    assert errs == []
    assert len(warns) == 1
    assert warns[0].code == ErrorCatalog.SYNTAX_MARKDOWN_BLOCK
    assert parsed["target"]["base_url"] == "https://example.com"


def test_trailing_comma_rejection():
    raw = '{"target": {"base_url": "https://example.com",}}'
    parsed, errs, warns = SyntaxValidator.validate(raw)
    assert parsed is None
    assert len(errs) >= 1
    assert errs[0].code == ErrorCatalog.SYNTAX_INVALID_JSON
    assert "Trailing comma" in errs[0].repair_hint


def test_null_or_empty_input():
    parsed, errs, warns = SyntaxValidator.validate(None)
    assert parsed is None
    assert errs[0].code == ErrorCatalog.SYNTAX_EMPTY_PAYLOAD

    parsed, errs, warns = SyntaxValidator.validate("   ")
    assert parsed is None
    assert errs[0].code == ErrorCatalog.SYNTAX_EMPTY_PAYLOAD
