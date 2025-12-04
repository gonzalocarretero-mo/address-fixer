"""
Address parsing using libpostal.

Extracts structured components from unstructured Spanish address strings.
"""

from dataclasses import dataclass
from postal.parser import parse_address


@dataclass
class ParsedAddress:
    """Structured address components extracted from raw text."""

    raw: str  # Original input
    road: str | None = None  # Street name
    house_number: str | None = None  # Building number
    unit: str | None = None  # Apartment/floor (level, unit)
    city: str | None = None
    postcode: str | None = None
    state_district: str | None = None  # Province/region
    country: str | None = None

    @property
    def has_postcode(self) -> bool:
        return self.postcode is not None and len(self.postcode) > 0

    @property
    def has_city(self) -> bool:
        return self.city is not None and len(self.city) > 0

    @property
    def has_road(self) -> bool:
        return self.road is not None and len(self.road) > 0

    @property
    def street_address(self) -> str:
        """Combine road, house_number, and unit into street address."""
        parts = []
        if self.road:
            parts.append(self.road)
        if self.house_number:
            parts.append(self.house_number)
        if self.unit:
            parts.append(self.unit)
        return " ".join(parts)


def parse(raw_address: str) -> ParsedAddress:
    """Parse a raw address string into structured components.

    Uses libpostal for parsing, which handles international address formats.

    Args:
        raw_address: Unstructured address string

    Returns:
        ParsedAddress with extracted components
    """
    if not raw_address or not raw_address.strip():
        return ParsedAddress(raw="")

    raw_address = raw_address.strip()
    result = ParsedAddress(raw=raw_address)

    # Parse with libpostal
    components = parse_address(raw_address)

    # Map libpostal labels to our fields
    # libpostal can return multiple values for same label, we take the first
    unit_parts = []

    for value, label in components:
        if label == "road" and result.road is None:
            result.road = value
        elif label == "house_number" and result.house_number is None:
            result.house_number = value
        elif label in ("level", "unit", "staircase"):
            unit_parts.append(value)
        elif label == "city" and result.city is None:
            result.city = value
        elif label == "postcode" and result.postcode is None:
            result.postcode = value
        elif label == "state_district" and result.state_district is None:
            result.state_district = value
        elif label == "country" and result.country is None:
            result.country = value

    # Combine unit parts
    if unit_parts:
        result.unit = ", ".join(unit_parts)

    return result


def parse_or_use_existing(
    raw_address: str,
    city: str | None = None,
    postcode: str | None = None,
) -> ParsedAddress:
    """Parse address, but prefer existing structured data if provided.

    Use this when CSV has separate columns that might or might not be filled.

    Args:
        raw_address: Address string (might contain everything, or just street)
        city: Pre-existing city value from CSV column
        postcode: Pre-existing postcode value from CSV column

    Returns:
        ParsedAddress with best available data
    """
    # Parse the raw address
    parsed = parse(raw_address)

    # If structured data was provided, prefer it over parsed values
    if city and city.strip():
        parsed.city = city.strip()

    if postcode and postcode.strip():
        parsed.postcode = postcode.strip()

    return parsed
