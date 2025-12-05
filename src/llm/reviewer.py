"""
LLM-based address review for edge cases.

Uses local Qwen model with Outlines for structured generation:
1. Semantic nonsense detection (gibberish, refusals, test data)
2. Unknown city validation (language variations)
"""

from enum import Enum
from typing import Literal

import outlines
from mlx_lm import load
from pydantic import BaseModel, Field


class AddressIntent(str, Enum):
    VALID_ATTEMPT = "valid_attempt"
    GIBBERISH = "gibberish"
    REFUSAL = "refusal"
    TEST_DATA = "test_data"


class NonsenseCheckOutput(BaseModel):
    """Structured output for nonsense detection."""

    classification: Literal["valid_attempt", "gibberish", "refusal", "test_data"] = Field(
        description="The intent classification"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level"
    )
    reason: str = Field(
        description="Brief explanation",
        max_length=100
    )


class CityValidationOutput(BaseModel):
    """Structured output for city validation."""

    is_valid: bool = Field(
        description="Whether the city name is valid for this province"
    )
    normalized_city: str = Field(
        description="The official Spanish city name, or 'none' if invalid",
        max_length=50
    )
    reason: str = Field(
        description="Brief explanation",
        max_length=100
    )


class NonsenseResult:
    """Result of nonsense check."""

    def __init__(self, intent: AddressIntent, confidence: str, explanation: str):
        self.intent = intent
        self.confidence = confidence
        self.explanation = explanation


class CityValidationResult:
    """Result of city validation."""

    def __init__(self, is_valid: bool, normalized_city: str | None, explanation: str):
        self.is_valid = is_valid
        self.normalized_city = normalized_city
        self.explanation = explanation


class AddressReviewer:
    """LLM-based reviewer for address edge cases using structured generation."""

    def __init__(self, model_path: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"):
        """Initialize the reviewer.

        Args:
            model_path: HuggingFace model path for mlx_lm
        """
        self.model_path = model_path
        self._model = None
        self._tokenizer = None
        self._outlines_model = None
        self._nonsense_generator = None
        self._city_generator = None

    def _ensure_loaded(self):
        """Lazy load the model and generators on first use."""
        if self._model is None:
            self._model, self._tokenizer = load(self.model_path)
            self._outlines_model = outlines.from_mlxlm(self._model, self._tokenizer)
            self._nonsense_generator = outlines.Generator(
                self._outlines_model, output_type=NonsenseCheckOutput
            )
            self._city_generator = outlines.Generator(
                self._outlines_model, output_type=CityValidationOutput
            )

    def check_nonsense(self, address: str) -> NonsenseResult:
        """Check if an address appears to be intentional nonsense.

        Args:
            address: Raw address string

        Returns:
            NonsenseResult with intent classification
        """
        self._ensure_loaded()

        prompt = f"""Analyze this Spanish address input and classify the user's intent.

Address: "{address}"

Classifications:
- valid_attempt: A genuine attempt to provide an address (typos/incomplete OK)
- gibberish: Random characters, keyboard mashing, meaningless text
- refusal: User refused to provide address (e.g., "No quiero", "No tengo")
- test_data: Obvious test/placeholder data (e.g., "TEST", "PRUEBA")

Return JSON with classification, confidence (high/medium/low), and reason."""

        json_str = self._nonsense_generator(prompt)
        result = NonsenseCheckOutput.model_validate_json(json_str)

        return NonsenseResult(
            intent=AddressIntent(result.classification),
            confidence=result.confidence,
            explanation=result.reason
        )

    def validate_city(
        self, city: str, postcode: str, province_cities: list[str]
    ) -> CityValidationResult:
        """Validate if a city name is a valid variant for a province.

        Args:
            city: City name from address
            postcode: Postal code (for context)
            province_cities: List of known cities in that province

        Returns:
            CityValidationResult with validation and normalized name
        """
        self._ensure_loaded()

        cities_str = ", ".join(province_cities[:10])

        prompt = f"""Is "{city}" a valid name for a city in Spanish province with postal code starting with {postcode[:2]}?

Reference cities in this province: {cities_str}

Answer is_valid=true if the city name matches or is a variant of any reference city.
Accept: exact matches, regional language variants, minor typos, missing accents.
Answer is_valid=false only for fictional places or cities in a different Spanish province."""

        json_str = self._city_generator(prompt)
        result = CityValidationOutput.model_validate_json(json_str)

        # Only return normalized city if marked as valid
        normalized = None
        if result.is_valid and result.normalized_city.lower() != "none":
            normalized = result.normalized_city

        return CityValidationResult(
            is_valid=result.is_valid,
            normalized_city=normalized,
            explanation=result.reason
        )
