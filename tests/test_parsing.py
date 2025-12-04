"""
Unit tests for address parsing.
"""

import pytest

from src.parsing.address import parse, parse_or_use_existing, ParsedAddress


class TestBasicParsing:
    """Test parsing of complete addresses."""

    def test_full_address_with_comma_separators(self):
        result = parse("Calle Gran Vía 32, 5ºA, Madrid, 28013")
        assert result.city == "madrid"
        assert result.postcode == "28013"
        assert result.road is not None

    def test_abbreviated_street(self):
        result = parse("c/ Serrano 110, bajo, Barcelona 08006")
        assert result.road == "c/ serrano"
        assert result.house_number == "110"
        assert result.unit == "bajo"
        assert result.city == "barcelona"
        assert result.postcode == "08006"

    def test_plaza_format(self):
        result = parse("Plaza de España 1-2, Sevilla 41001")
        assert result.road == "plaza de españa"
        assert result.house_number == "1-2"
        assert result.city == "sevilla"
        assert result.postcode == "41001"

    def test_avenue_with_floor(self):
        result = parse("Av. Diagonal 600, 2ª planta, Zaragoza 50009")
        assert result.road == "av. diagonal"
        assert result.house_number == "600"
        assert result.unit == "2ª planta"
        assert result.city == "zaragoza"
        assert result.postcode == "50009"

    def test_city_and_postcode_only(self):
        result = parse("Pozuelo de Alarcón 28223")
        assert result.city == "pozuelo de alarcón"
        assert result.postcode == "28223"


class TestPartialAddresses:
    """Test parsing of incomplete addresses."""

    def test_empty_string(self):
        result = parse("")
        assert result.raw == ""
        assert result.city is None
        assert result.postcode is None

    def test_whitespace_only(self):
        result = parse("   ")
        assert result.raw == ""

    def test_city_only(self):
        result = parse("Madrid")
        assert result.city == "madrid"
        assert result.postcode is None

    def test_postcode_only(self):
        result = parse("28013")
        assert result.postcode == "28013"


class TestParsedAddressProperties:
    """Test ParsedAddress helper properties."""

    def test_has_postcode_true(self):
        result = parse("Madrid 28013")
        assert result.has_postcode is True

    def test_has_postcode_false(self):
        result = parse("Madrid")
        assert result.has_postcode is False

    def test_has_city_true(self):
        result = parse("Madrid 28013")
        assert result.has_city is True

    def test_has_road_true(self):
        result = parse("Calle Serrano 110, Madrid")
        assert result.has_road is True

    def test_street_address_combined(self):
        result = parse("c/ Serrano 110, bajo, Barcelona 08006")
        street = result.street_address
        assert "c/ serrano" in street
        assert "110" in street
        assert "bajo" in street


class TestParseOrUseExisting:
    """Test parsing with pre-existing structured data."""

    def test_prefer_existing_city(self):
        result = parse_or_use_existing(
            raw_address="Calle Gran Vía 32, Madrid, 28013",
            city="Barcelona",  # Override
            postcode=None
        )
        assert result.city == "Barcelona"
        assert result.postcode == "28013"  # Parsed from raw

    def test_prefer_existing_postcode(self):
        result = parse_or_use_existing(
            raw_address="Calle Gran Vía 32, Madrid, 28013",
            city=None,
            postcode="08001"  # Override
        )
        assert result.city == "madrid"  # Parsed from raw
        assert result.postcode == "08001"

    def test_use_parsed_when_existing_empty(self):
        result = parse_or_use_existing(
            raw_address="Calle Gran Vía 32, Madrid, 28013",
            city="",
            postcode="  "
        )
        assert result.city == "madrid"
        assert result.postcode == "28013"

    def test_all_from_existing(self):
        result = parse_or_use_existing(
            raw_address="Calle Gran Vía 32",
            city="Madrid",
            postcode="28013"
        )
        assert result.city == "Madrid"
        assert result.postcode == "28013"
