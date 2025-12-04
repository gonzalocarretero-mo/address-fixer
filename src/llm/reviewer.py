"""
LLM-based address review for edge cases.

Uses local Qwen model for:
1. Semantic nonsense detection (gibberish, refusals, test data)
2. Unknown city validation (language variations)
"""

from dataclasses import dataclass
from enum import Enum
from mlx_lm import load, generate


class AddressIntent(Enum):
    VALID_ATTEMPT = "valid_attempt"  # Real attempt at an address
    GIBBERISH = "gibberish"  # Random characters, keyboard mashing
    REFUSAL = "refusal"  # User refused to provide address
    TEST_DATA = "test_data"  # Test/placeholder data
    UNCLEAR = "unclear"  # Model unsure


@dataclass
class NonsenseResult:
    intent: AddressIntent
    confidence: str  # "high", "medium", "low"
    explanation: str


@dataclass
class CityValidationResult:
    is_valid: bool
    normalized_city: str | None
    explanation: str


class AddressReviewer:
    """LLM-based reviewer for address edge cases."""

    def __init__(self, model_path: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"):
        """Load the model.

        Args:
            model_path: HuggingFace model path for mlx_lm
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None

    def _ensure_loaded(self):
        """Lazy load the model on first use."""
        if self.model is None:
            self.model, self.tokenizer = load(self.model_path)

    def _generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate a response from the model."""
        self._ensure_loaded()

        messages = [{"role": "user", "content": prompt}]
        formatted = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        response = generate(
            self.model,
            self.tokenizer,
            prompt=formatted,
            max_tokens=max_tokens
        )

        return response.strip()

    def check_nonsense(self, address: str) -> NonsenseResult:
        """Check if an address appears to be intentional nonsense.

        Args:
            address: Raw address string

        Returns:
            NonsenseResult with intent classification
        """
        prompt = f"""Analyze this Spanish address input and classify the user's intent.

Address: "{address}"

Classify as ONE of:
- VALID_ATTEMPT: A genuine attempt to provide an address (may have typos or be incomplete, that's OK)
- GIBBERISH: Random characters, keyboard mashing, meaningless text
- REFUSAL: User explicitly refused to provide address (e.g., "No quiero", "No tengo")
- TEST_DATA: Obvious test/placeholder data (e.g., "TEST", "PRUEBA", "asdfgh")

Respond in this exact format:
CLASSIFICATION: [one of the above]
CONFIDENCE: [high/medium/low]
REASON: [brief explanation]"""

        response = self._generate(prompt, max_tokens=80)

        # Parse response
        intent = AddressIntent.UNCLEAR
        confidence = "low"
        explanation = response

        lines = response.upper().split("\n")
        for line in lines:
            if "CLASSIFICATION:" in line:
                if "VALID_ATTEMPT" in line:
                    intent = AddressIntent.VALID_ATTEMPT
                elif "GIBBERISH" in line:
                    intent = AddressIntent.GIBBERISH
                elif "REFUSAL" in line:
                    intent = AddressIntent.REFUSAL
                elif "TEST_DATA" in line:
                    intent = AddressIntent.TEST_DATA
            elif "CONFIDENCE:" in line:
                if "HIGH" in line:
                    confidence = "high"
                elif "MEDIUM" in line:
                    confidence = "medium"
                elif "LOW" in line:
                    confidence = "low"

        # Extract reason if present
        for line in response.split("\n"):
            if line.upper().startswith("REASON:"):
                explanation = line.split(":", 1)[1].strip()
                break

        return NonsenseResult(
            intent=intent,
            confidence=confidence,
            explanation=explanation
        )

    def validate_city(self, city: str, postcode: str, province_cities: list[str]) -> CityValidationResult:
        """Validate if a city name is a valid variant for a province.

        Handles language variations (Catalan, Basque, Galician) and common misspellings.

        Args:
            city: City name from address
            postcode: Postal code (for context)
            province_cities: List of known cities in that province

        Returns:
            CityValidationResult with validation and normalized name
        """
        cities_str = ", ".join(province_cities[:10])  # Limit for prompt size

        prompt = f"""Does "{city}" refer to a city in Spanish postal code {postcode}?

Known cities in this area: {cities_str}

Answer YES if:
- Exact match (Lleida = Lleida)
- Language variant (Lérida = Lleida, Donostia = San Sebastián)
- Typo (Madird = Madrid)
- Missing accent (Malaga = Málaga)

Answer NO only if fictional or wrong province.

Format:
VALID: yes or no
NORMALIZED: correct city name, or none
REASON: one sentence"""

        response = self._generate(prompt, max_tokens=120)

        # Parse response
        is_valid = False
        normalized = None
        explanation = response

        lines = response.upper().split("\n")
        for line in lines:
            if "VALID:" in line:
                is_valid = "YES" in line
            elif "NORMALIZED:" in line:
                # Extract the normalized name (preserve original case from response)
                for orig_line in response.split("\n"):
                    if orig_line.upper().startswith("NORMALIZED:"):
                        norm_value = orig_line.split(":", 1)[1].strip()
                        if norm_value.lower() != "none":
                            normalized = norm_value
                        break

        # Extract reason if present
        for line in response.split("\n"):
            if line.upper().startswith("REASON:"):
                explanation = line.split(":", 1)[1].strip()
                break

        return CityValidationResult(
            is_valid=is_valid,
            normalized_city=normalized,
            explanation=explanation
        )
