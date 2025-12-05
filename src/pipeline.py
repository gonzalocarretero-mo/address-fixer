"""
Main address validation pipeline.

Orchestrates:
1. Parsing (libpostal)
2. Hard validation rules
3. City-postal code matching
4. LLM review for edge cases
"""

import csv
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from src.parsing.address import parse, parse_or_use_existing, ParsedAddress
from src.validation.rules import validate_hard_rules, get_violations, RuleViolation
from src.validation.postal_codes import PostalCodeValidator, ValidationStatus
from src.llm.reviewer import AddressReviewer, AddressIntent


class AddressStatus(str, Enum):
    """Final status after all validation stages."""

    VALID = "valid"  # Passed all checks
    VALID_NORMALIZED = "valid_normalized"  # Valid but normalized (typos fixed, etc.)
    INVALID_FORMAT = "invalid_format"  # Failed hard rules (empty, bad postcode format)
    INVALID_MISMATCH = "invalid_mismatch"  # City doesn't match postal code province
    NONSENSE = "nonsense"  # Gibberish, refusal, or test data
    UNKNOWN = "unknown"  # Couldn't determine validity
    NEEDS_REVIEW = "needs_review"  # LLM uncertain, needs human review


@dataclass
class ValidationResult:
    """Complete validation result for an address."""

    # Original input
    raw_address: str
    raw_city: str
    raw_postcode: str

    # Parsed components
    parsed: ParsedAddress

    # Final status
    status: AddressStatus
    message: str

    # Normalized values (if applicable)
    normalized_city: str | None = None
    normalized_postcode: str | None = None

    # Details from each stage
    rule_violations: list[str] = field(default_factory=list)
    city_postal_status: str | None = None
    llm_intent: str | None = None
    llm_confidence: str | None = None


class AddressPipeline:
    """Main pipeline for validating and cleaning addresses."""

    def __init__(
        self,
        reference_dir: Path,
        use_llm: bool = True,
        model_path: str = "mlx-community/Qwen2.5-7B-Instruct-4bit",
    ):
        """Initialize the pipeline.

        Args:
            reference_dir: Path to postal code reference data
            use_llm: Whether to use LLM for edge cases (slower but more accurate)
            model_path: HuggingFace model path for LLM
        """
        self.postal_validator = PostalCodeValidator(reference_dir)
        self.use_llm = use_llm
        self._llm_reviewer = None
        self._model_path = model_path

    @property
    def llm_reviewer(self) -> AddressReviewer:
        """Lazy load LLM reviewer."""
        if self._llm_reviewer is None:
            self._llm_reviewer = AddressReviewer(self._model_path)
        return self._llm_reviewer

    def validate(
        self,
        address: str,
        city: str = "",
        postcode: str = "",
    ) -> ValidationResult:
        """Validate a single address through all pipeline stages.

        Args:
            address: Street address (may contain city/postcode if unstructured)
            city: City name (optional, used if provided)
            postcode: Postal code (optional, used if provided)

        Returns:
            ValidationResult with status and details
        """
        # Stage 1: Parse address
        parsed = parse_or_use_existing(address, city, postcode)

        result = ValidationResult(
            raw_address=address,
            raw_city=city,
            raw_postcode=postcode,
            parsed=parsed,
            status=AddressStatus.UNKNOWN,
            message="",
        )

        # Stage 2: Hard validation rules
        violations = get_violations(parsed)
        result.rule_violations = [v.message for v in violations]

        if violations:
            # Check what type of violation
            violation_types = {v.violation for v in violations}

            if RuleViolation.EMPTY_ADDRESS in violation_types:
                result.status = AddressStatus.INVALID_FORMAT
                result.message = "Address is empty"
                return result

            if RuleViolation.TOO_SHORT in violation_types:
                result.status = AddressStatus.INVALID_FORMAT
                result.message = "Address too short"
                return result

            if RuleViolation.ONLY_NUMBERS in violation_types:
                result.status = AddressStatus.INVALID_FORMAT
                result.message = "Address contains only numbers"
                return result

            if RuleViolation.INVALID_POSTCODE_FORMAT in violation_types:
                result.status = AddressStatus.INVALID_FORMAT
                result.message = "Invalid postal code format"
                return result

            if RuleViolation.INVALID_POSTCODE_PROVINCE in violation_types:
                result.status = AddressStatus.INVALID_FORMAT
                result.message = "Invalid postal code province (must be 01-52)"
                return result

        # Stage 3: LLM nonsense detection on the street address (if enabled)
        # Do this before city validation to catch gibberish addresses
        # Check the road if available, otherwise check the raw address
        # (libpostal sometimes parses gibberish as "house" instead of "road")
        text_to_check = parsed.road if parsed.has_road else address
        if self.use_llm and text_to_check:
            nonsense_result = self.llm_reviewer.check_nonsense(text_to_check)
            result.llm_intent = nonsense_result.intent.value
            result.llm_confidence = nonsense_result.confidence

            if nonsense_result.intent in (
                AddressIntent.GIBBERISH,
                AddressIntent.TEST_DATA,
            ):
                result.status = AddressStatus.NONSENSE
                result.message = f"Street address is {nonsense_result.intent.value}: {nonsense_result.explanation}"
                return result
            elif nonsense_result.intent == AddressIntent.REFUSAL:
                result.status = AddressStatus.NONSENSE
                result.message = f"User refused to provide address: {nonsense_result.explanation}"
                return result

        # Stage 4: City-postal code validation (if both present)
        if parsed.has_city and parsed.has_postcode:
            city_result = self.postal_validator.validate(parsed.city, parsed.postcode)
            result.city_postal_status = city_result.status.value

            if city_result.status == ValidationStatus.VALID:
                result.status = AddressStatus.VALID
                result.message = "City matches postal code province"
                result.normalized_city = parsed.city
                result.normalized_postcode = parsed.postcode
                return result

            elif city_result.status == ValidationStatus.INVALID:
                result.status = AddressStatus.INVALID_MISMATCH
                result.message = city_result.message
                return result

            elif city_result.status == ValidationStatus.UNKNOWN_CITY:
                # City not in database - try LLM if enabled
                if self.use_llm:
                    province_cities = self.postal_validator.get_cities_for_province(
                        parsed.postcode[:2]
                    )
                    llm_result = self.llm_reviewer.validate_city(
                        parsed.city, parsed.postcode, province_cities
                    )
                    result.llm_confidence = "city_validation"

                    if llm_result.is_valid:
                        result.status = AddressStatus.VALID_NORMALIZED
                        result.message = f"City validated by LLM: {llm_result.explanation}"
                        result.normalized_city = llm_result.normalized_city or parsed.city
                        result.normalized_postcode = parsed.postcode
                        return result
                    else:
                        result.status = AddressStatus.NEEDS_REVIEW
                        result.message = f"City unknown: {llm_result.explanation}"
                        return result
                else:
                    result.status = AddressStatus.NEEDS_REVIEW
                    result.message = "City not found in database"
                    return result

        # Stage 5: Final fallback for addresses without city/postcode
        if self.use_llm and result.status == AddressStatus.UNKNOWN:
            # Already checked nonsense in stage 3, so if we're here it's a valid attempt
            if parsed.has_city or parsed.has_postcode:
                result.status = AddressStatus.VALID
                result.message = "Appears to be a valid address attempt"
            else:
                result.status = AddressStatus.NEEDS_REVIEW
                result.message = "Valid attempt but missing city/postcode"

        # If we still don't have a status, mark as needs review
        if result.status == AddressStatus.UNKNOWN:
            result.status = AddressStatus.NEEDS_REVIEW
            result.message = "Could not validate without LLM"

        return result

    def process_csv(
        self,
        input_path: Path,
        output_path: Path,
        address_col: str = "address",
        city_col: str | None = "city",
        postcode_col: str | None = "zip",
        limit: int | None = None,
    ) -> dict:
        """Process a CSV file of addresses.

        Args:
            input_path: Path to input CSV
            output_path: Path to output CSV
            address_col: Column name for address
            city_col: Column name for city (optional)
            postcode_col: Column name for postal code (optional)
            limit: Maximum rows to process (for testing)

        Returns:
            Summary statistics
        """
        stats = {
            "total": 0,
            "valid": 0,
            "valid_normalized": 0,
            "invalid_format": 0,
            "invalid_mismatch": 0,
            "nonsense": 0,
            "needs_review": 0,
            "unknown": 0,
        }

        with open(input_path, "r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames or []

            # Add output columns
            output_fields = fieldnames + [
                "validation_status",
                "validation_message",
                "normalized_city",
                "normalized_postcode",
                "parsed_road",
                "parsed_city",
                "parsed_postcode",
            ]

            with open(output_path, "w", encoding="utf-8", newline="") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=output_fields)
                writer.writeheader()

                for i, row in enumerate(reader):
                    if limit and i >= limit:
                        break

                    stats["total"] += 1

                    # Extract fields
                    address = row.get(address_col, "")
                    city = row.get(city_col, "") if city_col else ""
                    postcode = row.get(postcode_col, "") if postcode_col else ""

                    # Validate
                    result = self.validate(address, city, postcode)

                    # Update stats
                    status_key = result.status.value.replace("-", "_")
                    if status_key in stats:
                        stats[status_key] += 1

                    # Write output row
                    output_row = dict(row)
                    output_row["validation_status"] = result.status.value
                    output_row["validation_message"] = result.message
                    output_row["normalized_city"] = result.normalized_city or ""
                    output_row["normalized_postcode"] = result.normalized_postcode or ""
                    output_row["parsed_road"] = result.parsed.road or ""
                    output_row["parsed_city"] = result.parsed.city or ""
                    output_row["parsed_postcode"] = result.parsed.postcode or ""

                    writer.writerow(output_row)

                    # Progress
                    if stats["total"] % 100 == 0:
                        print(f"Processed {stats['total']} addresses...")

        return stats
