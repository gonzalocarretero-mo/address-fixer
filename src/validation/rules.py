"""
Hard validation rules for Spanish addresses.

Simple deterministic checks that don't require LLM.
"""

from dataclasses import dataclass
from enum import Enum

from src.parsing.address import ParsedAddress


class RuleViolation(Enum):
    NONE = "none"
    EMPTY_ADDRESS = "empty_address"
    TOO_SHORT = "too_short"
    INVALID_POSTCODE_FORMAT = "invalid_postcode_format"
    INVALID_POSTCODE_PROVINCE = "invalid_postcode_province"
    ONLY_NUMBERS = "only_numbers"


@dataclass
class RuleResult:
    is_valid: bool
    violation: RuleViolation
    message: str


# Valid Spanish province codes: 01-52
VALID_PROVINCE_CODES = {f"{i:02d}" for i in range(1, 53)}


def check_postcode_format(postcode: str | None) -> RuleResult:
    """Check if postcode has valid 5-digit format."""
    if not postcode:
        return RuleResult(
            is_valid=True,  # Missing is not invalid, just incomplete
            violation=RuleViolation.NONE,
            message="No postcode provided"
        )

    postcode = postcode.strip()

    if not postcode.isdigit():
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.INVALID_POSTCODE_FORMAT,
            message=f"Postcode '{postcode}' contains non-numeric characters"
        )

    if len(postcode) != 5:
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.INVALID_POSTCODE_FORMAT,
            message=f"Postcode '{postcode}' must be exactly 5 digits"
        )

    return RuleResult(
        is_valid=True,
        violation=RuleViolation.NONE,
        message="Valid postcode format"
    )


def check_postcode_province(postcode: str | None) -> RuleResult:
    """Check if postcode has valid Spanish province prefix (01-52)."""
    if not postcode or len(postcode) < 2:
        return RuleResult(
            is_valid=True,
            violation=RuleViolation.NONE,
            message="No postcode to check"
        )

    province = postcode[:2]

    if province not in VALID_PROVINCE_CODES:
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.INVALID_POSTCODE_PROVINCE,
            message=f"Province code '{province}' is not valid (must be 01-52)"
        )

    return RuleResult(
        is_valid=True,
        violation=RuleViolation.NONE,
        message=f"Valid province code: {province}"
    )


def check_not_empty(parsed: ParsedAddress) -> RuleResult:
    """Check if address has meaningful content."""
    if not parsed.raw or not parsed.raw.strip():
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.EMPTY_ADDRESS,
            message="Address is empty"
        )

    return RuleResult(
        is_valid=True,
        violation=RuleViolation.NONE,
        message="Address has content"
    )


def check_minimum_length(parsed: ParsedAddress, min_chars: int = 5) -> RuleResult:
    """Check if address has minimum meaningful characters."""
    meaningful = len([c for c in parsed.raw if c.isalnum()])

    if meaningful < min_chars:
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.TOO_SHORT,
            message=f"Address too short ({meaningful} chars, minimum {min_chars})"
        )

    return RuleResult(
        is_valid=True,
        violation=RuleViolation.NONE,
        message=f"Address length OK ({meaningful} chars)"
    )


def check_not_only_numbers(parsed: ParsedAddress) -> RuleResult:
    """Check if address contains letters, not just numbers."""
    # Check the raw input minus the postcode
    text = parsed.raw
    if parsed.postcode:
        text = text.replace(parsed.postcode, "")

    # Remove common separators
    text = text.replace(",", "").replace(".", "").replace("-", "").strip()

    has_letters = any(c.isalpha() for c in text)

    if not has_letters:
        return RuleResult(
            is_valid=False,
            violation=RuleViolation.ONLY_NUMBERS,
            message="Address contains only numbers"
        )

    return RuleResult(
        is_valid=True,
        violation=RuleViolation.NONE,
        message="Address contains letters"
    )


def validate_hard_rules(parsed: ParsedAddress) -> list[RuleResult]:
    """Run all hard validation rules on a parsed address.

    Returns list of all rule results (both passed and failed).
    """
    results = [
        check_not_empty(parsed),
        check_minimum_length(parsed),
        check_not_only_numbers(parsed),
        check_postcode_format(parsed.postcode),
        check_postcode_province(parsed.postcode),
    ]

    return results


def get_violations(parsed: ParsedAddress) -> list[RuleResult]:
    """Get only the failed rules for a parsed address."""
    all_results = validate_hard_rules(parsed)
    return [r for r in all_results if not r.is_valid]
