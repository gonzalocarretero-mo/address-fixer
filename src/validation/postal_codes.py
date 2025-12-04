"""
Postal code validation for Spanish addresses.

Validates that city names match their postal code province (first 2 digits).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.normalization.text import normalize_city, extract_city_variants


class ValidationStatus(Enum):
    VALID = "valid"  # City matches postal code province
    INVALID = "invalid"  # City exists but wrong province
    UNKNOWN_CITY = "unknown_city"  # City not in our database
    MISSING_DATA = "missing_data"  # City or postal code is empty/invalid


@dataclass
class ValidationResult:
    status: ValidationStatus
    message: str
    province_code: str | None = None
    expected_cities: list[str] | None = None


class PostalCodeValidator:
    """Validates Spanish city + postal code pairs."""

    def __init__(self, reference_dir: Path):
        """Load reference data from codciu.txt. It contains an index to the corresponding file of a city. A file of a city contains its postal code - streets pairs.

        Args:
            reference_dir: Path to directory containing codciu.txt
        """
        self.reference_dir = reference_dir

        # Province code (2 digits) → list of city names
        self.province_to_cities: dict[str, list[str]] = {}

        # Normalized city name → province code (2 digits)
        self.city_to_province: dict[str, str] = {}

        # City variant (partial name) → full city names
        self.variant_to_cities: dict[str, list[str]] = {}

        self._load_reference_data()

    def _load_reference_data(self) -> None:
        """Load and parse codciu.txt."""
        codciu_path = self.reference_dir / "codciu.txt"

        with open(codciu_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Format: 3-char code + city name
                # e.g., "286Pozuelo de Alarcón" or "28xMadrid"
                if len(line) < 4:
                    continue

                code = line[:3]
                city = line[3:].strip()

                if not city:
                    continue

                # Extract province (first 2 digits)
                province = code[:2]

                # Handle entries with multiple names (e.g., "Alacant-Alicante")
                city_names = self._split_city_names(city)

                for city_name in city_names:
                    # Add to province → cities mapping
                    if province not in self.province_to_cities:
                        self.province_to_cities[province] = []
                    self.province_to_cities[province].append(city_name)

                    # Add to city → province mapping (normalized)
                    normalized = normalize_city(city_name)
                    self.city_to_province[normalized] = province

                    # Add variants for partial matching
                    for variant in extract_city_variants(city_name):
                        if variant not in self.variant_to_cities:
                            self.variant_to_cities[variant] = []
                        if city_name not in self.variant_to_cities[variant]:
                            self.variant_to_cities[variant].append(city_name)

    def _split_city_names(self, city: str) -> list[str]:
        """Split city entries with multiple names.

        Examples:
            "Alacant-Alicante" → ["Alacant", "Alicante"]
            "Donostia - San Sebastian" → ["Donostia", "San Sebastian"]
            "Hospitalet de Llobregat,l'" → ["Hospitalet de Llobregat", "l'Hospitalet de Llobregat"]
        """
        names = []

        # Handle "Name,l'" format (Catalan article at end)
        if city.endswith(",l'"):
            base = city[:-3]
            names.append(base)
            names.append(f"l'{base}")
        elif ",Las" in city:
            # "Palmas de Gran Canaria,Las" → "Las Palmas de Gran Canaria"
            parts = city.split(",Las")
            base = parts[0].strip()
            names.append(base)
            names.append(f"Las {base}")
        elif " - " in city:
            # "Donostia - San Sebastian" → ["Donostia", "San Sebastian"]
            names.extend([n.strip() for n in city.split(" - ")])
        elif "-" in city and not any(c.isspace() for c in city.split("-")[0]):
            # "Alacant-Alicante" but not "Vitoria-Gasteiz" (which is one name)
            parts = city.split("-")
            # Heuristic: if both parts look like separate names (capitalized), split
            if len(parts) == 2 and parts[0][0].isupper() and parts[1][0].isupper():
                # Check if it's a bilingual name vs compound name
                # Bilingual: Alacant-Alicante, Elx-Elche
                # Compound: Vitoria-Gasteiz, Rivas-Vaciamadrid
                # Heuristic: bilingual names are usually short and similar length
                if abs(len(parts[0]) - len(parts[1])) < 5 and len(parts[0]) < 12:
                    names.extend([p.strip() for p in parts])
                else:
                    names.append(city)
            else:
                names.append(city)
        else:
            names.append(city)

        return names

    def validate(self, city: str, postal_code: str) -> ValidationResult:
        """Validate that a city matches its postal code province.

        Args:
            city: City name (can be unnormalized)
            postal_code: 5-digit Spanish postal code

        Returns:
            ValidationResult with status and details
        """
        # Check for missing data
        if not city or not city.strip():
            return ValidationResult(
                status=ValidationStatus.MISSING_DATA,
                message="City is empty"
            )

        if not postal_code or not postal_code.strip():
            return ValidationResult(
                status=ValidationStatus.MISSING_DATA,
                message="Postal code is empty"
            )

        postal_code = postal_code.strip()

        # Validate postal code format
        if not postal_code.isdigit() or len(postal_code) != 5:
            return ValidationResult(
                status=ValidationStatus.MISSING_DATA,
                message=f"Invalid postal code format: {postal_code}"
            )

        province = postal_code[:2]

        # Check if province exists
        if province not in self.province_to_cities:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"Unknown province code: {province}",
                province_code=province
            )

        # Normalize city for lookup
        normalized_city = normalize_city(city)

        # Try exact match first
        if normalized_city in self.city_to_province:
            expected_province = self.city_to_province[normalized_city]
            if expected_province == province:
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    message="City matches postal code province",
                    province_code=province
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"City '{city}' belongs to province {expected_province}, not {province}",
                    province_code=province,
                    expected_cities=self.province_to_cities.get(province, [])
                )

        # Try variant/partial match
        city_variants = extract_city_variants(city)
        for variant in city_variants:
            if variant in self.variant_to_cities:
                # Found a partial match - check if any match the province
                matching_cities = self.variant_to_cities[variant]
                for matched_city in matching_cities:
                    matched_normalized = normalize_city(matched_city)
                    if matched_normalized in self.city_to_province:
                        expected_province = self.city_to_province[matched_normalized]
                        if expected_province == province:
                            return ValidationResult(
                                status=ValidationStatus.VALID,
                                message=f"City '{city}' matches '{matched_city}' in province {province}",
                                province_code=province
                            )

                # Partial match found but wrong province
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"City '{city}' found but not in province {province}",
                    province_code=province,
                    expected_cities=self.province_to_cities.get(province, [])
                )

        # City not found in database
        return ValidationResult(
            status=ValidationStatus.UNKNOWN_CITY,
            message=f"City '{city}' not found in database (province {province})",
            province_code=province,
            expected_cities=self.province_to_cities.get(province, [])
        )

    def get_cities_for_province(self, province: str) -> list[str]:
        """Get all known cities for a province code."""
        return self.province_to_cities.get(province, [])

    def get_province_for_city(self, city: str) -> str | None:
        """Get province code for a city name."""
        normalized = normalize_city(city)
        return self.city_to_province.get(normalized)
