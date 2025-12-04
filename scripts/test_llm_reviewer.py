"""
Test script for LLM-based address review.

Run manually to test the model integration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.reviewer import AddressReviewer


def main():
    print("Loading model...")
    reviewer = AddressReviewer()

    # Test nonsense detection
    print("\n" + "=" * 60)
    print("NONSENSE DETECTION TESTS")
    print("=" * 60)

    test_addresses = [
        "Calle Gran Vía 32, Madrid",  # Valid
        "AAAAAAA BBBBBBB CCCCCC",  # Gibberish
        "asdfgh jklñ 12345",  # Keyboard mashing
        "No quiero dar mi dirección",  # Refusal
        "TEST TEST PRUEBA",  # Test data
        "c/ Serrano 110, bajo",  # Valid abbreviated
        "xkcd qwerty zzzz",  # Gibberish
        "Prefiero no decirlo",  # Refusal
    ]

    for addr in test_addresses:
        print(f"\nInput: {addr!r}")
        result = reviewer.check_nonsense(addr)
        print(f"  Intent: {result.intent.value}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reason: {result.explanation}")

    # Test city validation
    print("\n" + "=" * 60)
    print("CITY VALIDATION TESTS")
    print("=" * 60)

    city_tests = [
        ("Lleida", "25001", ["Lleida"]),  # Catalan, should match
        ("Lérida", "25001", ["Lleida"]),  # Spanish variant
        ("Donostia", "20001", ["Donostia - San Sebastian"]),  # Basque
        ("San Sebastián", "20001", ["Donostia - San Sebastian"]),  # Spanish
        ("Seville", "41001", ["Sevilla"]),  # English name
        ("Winterfell", "28001", ["Madrid", "Alcalá de Henares"]),  # Fictional
    ]

    for city, postcode, province_cities in city_tests:
        print(f"\nCity: {city!r}, Postcode: {postcode}")
        print(f"  Known cities: {province_cities}")
        result = reviewer.validate_city(city, postcode, province_cities)
        print(f"  Valid: {result.is_valid}")
        print(f"  Normalized: {result.normalized_city}")
        print(f"  Reason: {result.explanation}")


if __name__ == "__main__":
    main()
