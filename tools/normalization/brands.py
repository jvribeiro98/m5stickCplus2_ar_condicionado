"""Normalização conservadora de marcas, sem pesquisa externa."""

import re
import unicodedata

AMBIGUOUS = {"", "generic", "unknown", "misc", "other", "universal", "no brand"}


def brand_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def display_name(value: str) -> str:
    clean = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip())
    if clean.isupper() or clean.islower():
        return clean.title()
    return clean


def suggest_brand(original: str | None, source_path: str) -> dict:
    preserved = original
    if original is None or original.strip().casefold() in AMBIGUOUS:
        return {
            "original": preserved,
            "suggested_brand_id": None,
            "display_name": None,
            "manufacturer": None,
            "confidence": 0.0,
            "rule": "unresolved",
            "reasons": ["marca ausente ou genérica"],
            "evidence": [{"source": "inventory", "value": preserved, "path": source_path}],
            "requires_review": True,
        }

    slug = brand_slug(original)
    if not slug:
        return {
            "original": preserved,
            "suggested_brand_id": None,
            "display_name": None,
            "manufacturer": None,
            "confidence": 0.0,
            "rule": "unresolved",
            "reasons": ["grafia não produz identificador seguro"],
            "evidence": [{"source": "inventory", "value": preserved, "path": source_path}],
            "requires_review": True,
        }

    return {
        "original": preserved,
        "suggested_brand_id": slug,
        "display_name": display_name(original),
        "manufacturer": None,
        "confidence": 0.97,
        "rule": "typographic_normalization",
        "reasons": ["somente caixa, Unicode, espaços e pontuação foram normalizados"],
        "evidence": [{"source": "inventory", "value": preserved, "path": source_path}],
        "requires_review": False,
    }
