"""
Text normalization utilities for Spanish addresses.
"""

import unicodedata


def remove_accents(text: str) -> str:
    """Remove accents from text, keeping base characters.

    Example: "Málaga" → "Malaga", "Alarcón" → "Alarcon"
    """
    # Normalize to decomposed form (separate base char from accent)
    normalized = unicodedata.normalize("NFD", text)
    # Keep only non-combining characters (remove accents)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def normalize_for_comparison(text: str) -> str:
    """Normalize text for fuzzy comparison.

    - Lowercase
    - Remove accents
    - Strip whitespace
    - Collapse multiple spaces
    """
    text = text.lower()
    text = remove_accents(text)
    text = " ".join(text.split())  # Collapse whitespace
    return text.strip()


def normalize_city(city: str) -> str:
    """Normalize city name for lookup.

    Handles common variations like:
    - "Pozuelo de Alarcón" → "pozuelo de alarcon"
    - "L'Hospitalet" → "l'hospitalet" (keep apostrophe)
    - "Vitoria-Gasteiz" → "vitoria-gasteiz" (keep hyphen)
    """
    return normalize_for_comparison(city)


def extract_city_variants(city: str) -> list[str]:
    """Generate variants of a city name for matching.

    Example: "Pozuelo de Alarcón" →
        ["pozuelo de alarcon", "pozuelo", "alarcon"]
    """
    normalized = normalize_city(city)
    variants = [normalized]

    # Add individual words (for partial matching like "Pozuelo")
    words = normalized.replace("-", " ").replace("'", " ").split()

    # Filter out common articles/prepositions
    stopwords = {"de", "del", "la", "el", "los", "las", "l", "d", "en", "a"}
    meaningful_words = [w for w in words if w not in stopwords and len(w) > 2]

    variants.extend(meaningful_words)

    return list(set(variants))
