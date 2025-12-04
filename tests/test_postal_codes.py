"""
Unit tests for postal code validation.
"""

import pytest
from pathlib import Path

from src.validation.postal_codes import PostalCodeValidator, ValidationStatus


@pytest.fixture
def validator():
    """Create validator with reference data."""
    project_root = Path(__file__).parent.parent
    reference_dir = project_root / "data" / "reference" / "postal-codes"
    return PostalCodeValidator(reference_dir)


class TestValidCityPostalPairs:
    """Test cases where city matches postal code province."""

    def test_madrid_valid(self, validator):
        result = validator.validate("Madrid", "28013")
        assert result.status == ValidationStatus.VALID

    def test_lowercase_city(self, validator):
        result = validator.validate("madrid", "28013")
        assert result.status == ValidationStatus.VALID

    def test_uppercase_city(self, validator):
        result = validator.validate("MADRID", "28013")
        assert result.status == ValidationStatus.VALID

    def test_barcelona_valid(self, validator):
        result = validator.validate("Barcelona", "08001")
        assert result.status == ValidationStatus.VALID

    def test_city_with_accent(self, validator):
        result = validator.validate("Málaga", "29000")
        assert result.status == ValidationStatus.VALID

    def test_city_without_accent(self, validator):
        result = validator.validate("Malaga", "29000")
        assert result.status == ValidationStatus.VALID

    def test_full_city_name(self, validator):
        result = validator.validate("Pozuelo de Alarcón", "28223")
        assert result.status == ValidationStatus.VALID

    def test_partial_city_name(self, validator):
        result = validator.validate("Pozuelo", "28223")
        assert result.status == ValidationStatus.VALID

    def test_partial_city_lowercase(self, validator):
        result = validator.validate("pozuelo", "28224")
        assert result.status == ValidationStatus.VALID


class TestBilingualCityNames:
    """Test Catalan, Basque, Galician name variants."""

    def test_catalan_lleida(self, validator):
        result = validator.validate("Lleida", "25001")
        assert result.status == ValidationStatus.VALID

    def test_catalan_alacant(self, validator):
        result = validator.validate("Alacant", "03001")
        assert result.status == ValidationStatus.VALID

    def test_spanish_alicante(self, validator):
        result = validator.validate("Alicante", "03001")
        assert result.status == ValidationStatus.VALID

    def test_basque_donostia(self, validator):
        result = validator.validate("Donostia", "20001")
        assert result.status == ValidationStatus.VALID

    def test_spanish_san_sebastian(self, validator):
        result = validator.validate("San Sebastian", "20001")
        assert result.status == ValidationStatus.VALID

    def test_compound_name_vitoria_gasteiz(self, validator):
        result = validator.validate("Vitoria-Gasteiz", "01001")
        assert result.status == ValidationStatus.VALID

    def test_partial_compound_vitoria(self, validator):
        result = validator.validate("Vitoria", "01001")
        assert result.status == ValidationStatus.VALID


class TestInvalidCityPostalPairs:
    """Test cases where city does NOT match postal code province."""

    def test_madrid_with_barcelona_postal(self, validator):
        result = validator.validate("Madrid", "08001")
        assert result.status == ValidationStatus.INVALID
        assert result.province_code == "08"

    def test_barcelona_with_madrid_postal(self, validator):
        result = validator.validate("Barcelona", "28013")
        assert result.status == ValidationStatus.INVALID
        assert result.province_code == "28"

    def test_invalid_province_code(self, validator):
        result = validator.validate("Falseland", "99999")
        assert result.status == ValidationStatus.INVALID


class TestUnknownCities:
    """Test cases where city is not in our database."""

    def test_english_city_name(self, validator):
        result = validator.validate("Seville", "41001")
        assert result.status == ValidationStatus.UNKNOWN_CITY

    def test_fictional_city(self, validator):
        result = validator.validate("Winterfell", "28001")
        assert result.status == ValidationStatus.UNKNOWN_CITY


class TestMissingData:
    """Test cases with missing or invalid data."""

    def test_empty_city(self, validator):
        result = validator.validate("", "28013")
        assert result.status == ValidationStatus.MISSING_DATA

    def test_empty_postal_code(self, validator):
        result = validator.validate("Madrid", "")
        assert result.status == ValidationStatus.MISSING_DATA

    def test_short_postal_code(self, validator):
        result = validator.validate("Madrid", "2801")
        assert result.status == ValidationStatus.MISSING_DATA

    def test_non_numeric_postal_code(self, validator):
        result = validator.validate("Madrid", "ABCDE")
        assert result.status == ValidationStatus.MISSING_DATA

    def test_whitespace_city(self, validator):
        result = validator.validate("   ", "28013")
        assert result.status == ValidationStatus.MISSING_DATA
