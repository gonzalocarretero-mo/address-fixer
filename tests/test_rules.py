"""
Unit tests for hard validation rules.
"""

import pytest

from src.parsing.address import ParsedAddress
from src.validation.rules import (
    check_postcode_format,
    check_postcode_province,
    check_not_empty,
    check_minimum_length,
    check_not_only_numbers,
    validate_hard_rules,
    get_violations,
    RuleViolation,
)


class TestPostcodeFormat:
    """Test postcode format validation."""

    def test_valid_postcode(self):
        result = check_postcode_format("28013")
        assert result.is_valid

    def test_too_short(self):
        result = check_postcode_format("2801")
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_FORMAT

    def test_too_long(self):
        result = check_postcode_format("280130")
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_FORMAT

    def test_non_numeric(self):
        result = check_postcode_format("28O13")  # Letter O instead of 0
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_FORMAT

    def test_empty_postcode(self):
        result = check_postcode_format("")
        assert result.is_valid  # Missing is OK, just incomplete

    def test_none_postcode(self):
        result = check_postcode_format(None)
        assert result.is_valid


class TestPostcodeProvince:
    """Test postcode province validation (first 2 digits must be 01-52)."""

    def test_valid_madrid_28(self):
        result = check_postcode_province("28013")
        assert result.is_valid

    def test_valid_barcelona_08(self):
        result = check_postcode_province("08001")
        assert result.is_valid

    def test_valid_minimum_01(self):
        result = check_postcode_province("01001")
        assert result.is_valid

    def test_valid_maximum_52(self):
        result = check_postcode_province("52001")
        assert result.is_valid

    def test_invalid_00(self):
        result = check_postcode_province("00000")
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_PROVINCE

    def test_invalid_99(self):
        result = check_postcode_province("99999")
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_PROVINCE

    def test_invalid_53(self):
        result = check_postcode_province("53001")
        assert not result.is_valid
        assert result.violation == RuleViolation.INVALID_POSTCODE_PROVINCE


class TestNotEmpty:
    """Test empty address detection."""

    def test_valid_address(self):
        parsed = ParsedAddress(raw="Calle Gran Vía 32, Madrid")
        result = check_not_empty(parsed)
        assert result.is_valid

    def test_empty_string(self):
        parsed = ParsedAddress(raw="")
        result = check_not_empty(parsed)
        assert not result.is_valid
        assert result.violation == RuleViolation.EMPTY_ADDRESS

    def test_whitespace_only(self):
        parsed = ParsedAddress(raw="   ")
        result = check_not_empty(parsed)
        assert not result.is_valid
        assert result.violation == RuleViolation.EMPTY_ADDRESS


class TestMinimumLength:
    """Test minimum length validation."""

    def test_valid_length(self):
        parsed = ParsedAddress(raw="Calle Mayor 5")
        result = check_minimum_length(parsed)
        assert result.is_valid

    def test_too_short(self):
        parsed = ParsedAddress(raw="AB")
        result = check_minimum_length(parsed)
        assert not result.is_valid
        assert result.violation == RuleViolation.TOO_SHORT

    def test_exactly_minimum(self):
        parsed = ParsedAddress(raw="ABCDE")
        result = check_minimum_length(parsed, min_chars=5)
        assert result.is_valid


class TestNotOnlyNumbers:
    """Test number-only address detection."""

    def test_valid_with_letters(self):
        parsed = ParsedAddress(raw="Calle 42", postcode=None)
        result = check_not_only_numbers(parsed)
        assert result.is_valid

    def test_only_numbers(self):
        parsed = ParsedAddress(raw="12345 67890", postcode="12345")
        result = check_not_only_numbers(parsed)
        assert not result.is_valid
        assert result.violation == RuleViolation.ONLY_NUMBERS

    def test_postcode_excluded(self):
        # Address has only postcode, should fail
        parsed = ParsedAddress(raw="28013", postcode="28013")
        result = check_not_only_numbers(parsed)
        assert not result.is_valid


class TestValidateHardRules:
    """Test combined validation."""

    def test_valid_address_passes_all(self):
        parsed = ParsedAddress(
            raw="Calle Gran Vía 32, Madrid, 28013",
            postcode="28013"
        )
        results = validate_hard_rules(parsed)
        assert all(r.is_valid for r in results)

    def test_get_violations_empty_for_valid(self):
        parsed = ParsedAddress(
            raw="Calle Gran Vía 32, Madrid, 28013",
            postcode="28013"
        )
        violations = get_violations(parsed)
        assert len(violations) == 0

    def test_get_violations_returns_failures(self):
        parsed = ParsedAddress(
            raw="AB",
            postcode="99999"
        )
        violations = get_violations(parsed)
        assert len(violations) >= 2  # Too short + invalid province
