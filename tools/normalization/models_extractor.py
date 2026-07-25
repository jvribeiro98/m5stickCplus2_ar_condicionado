"""Extração conservadora de candidatos de modelo."""

import re
import unicodedata
from pathlib import PurePosixPath

from .models import InventoryRecord

STOPWORDS = {
    "unknown",
    "remote",
    "remote control",
    "control",
    "controller",
    "universal",
    "device",
    "test",
    "sample",
    "example",
    "demo",
    "generic",
    "misc",
    "miscellaneous",
    "tv",
    "television",
    "ac",
    "air conditioner",
    "fan",
    "projector",
    "receiver",
    "soundbar",
    "dvd",
    "blu ray",
    "codes",
    "codeset",
    "database",
    "converted",
}
GENERIC_NUMBERED = re.compile(r"(?i)^(?:remote|device|test|sample|example|code|codeset)[ _-]*\d+$")
COMMERCIAL_TOKEN = re.compile(r"(?i)^(?=.{3,48}$)(?=.*[a-z])(?=.*\d)[a-z0-9][a-z0-9._+,-]*$")


def _normalized(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _is_brand_or_category(value: str, record: InventoryRecord) -> bool:
    candidate = _normalized(value)
    brand = _normalized(record.original_brand)
    category = _normalized(record.original_category)
    return candidate in {brand, category} or candidate in STOPWORDS


def _commercial_candidate(value: str, record: InventoryRecord) -> str | None:
    clean = value.strip().removesuffix(".ir").strip("()[]{}., ")
    if not clean or _is_brand_or_category(clean, record):
        return None
    normalized_parts = set(_normalized(clean).split())
    brand_parts = set(_normalized(record.original_brand).split())
    if normalized_parts and normalized_parts <= STOPWORDS | brand_parts:
        return None
    if GENERIC_NUMBERED.fullmatch(clean):
        return None
    if clean.replace("_", "").replace("-", "").isdigit():
        return None

    brand = _normalized(record.original_brand)
    parts = [part for part in re.split(r"[\s/]+", clean) if part]
    filtered = [part for part in parts if _normalized(part) != brand]
    for part in filtered:
        token = part.strip("()[]{}., ")
        if COMMERCIAL_TOKEN.fullmatch(token) and not GENERIC_NUMBERED.fullmatch(token):
            return token
    joined = "_".join(filtered)
    if COMMERCIAL_TOKEN.fullmatch(joined) and not GENERIC_NUMBERED.fullmatch(joined):
        return joined
    return None


def _clean_unknown_prefix(value: str) -> tuple[str, bool]:
    match = re.fullmatch(r"(?i)unknown[\s_-]+(.+)", value.strip())
    if not match:
        return value, False
    return match.group(1).strip(), True


def extract_model(record: InventoryRecord) -> dict:
    path = PurePosixPath(record.source_path.replace("\\", "/"))
    evidence: list[tuple[str, str, float, bool]] = []
    unknown_numeric_removed = False

    def add_evidence(source: str, value: str, confidence: float) -> None:
        nonlocal unknown_numeric_removed
        cleaned, was_cleaned = _clean_unknown_prefix(value)
        candidate = _commercial_candidate(cleaned, record)
        if candidate:
            evidence.append(
                (
                    source,
                    candidate,
                    min(confidence, 0.58) if was_cleaned else confidence,
                    was_cleaned,
                )
            )
        elif was_cleaned and cleaned.isdigit():
            unknown_numeric_removed = True

    if record.original_model:
        confidence = record.model_confidence or 0.62
        add_evidence("inventory.model", record.original_model, min(confidence, 0.78))
    add_evidence("file_name", path.stem, 0.72)
    add_evidence("parent_directory", path.parent.name, 0.68)
    for comment in record.comments:
        add_evidence("comment", comment, 0.6)

    unique: list[tuple[str, str, float, bool]] = []
    positions = {}
    for item in evidence:
        key = _normalized(item[1])
        if key and key not in positions:
            positions[key] = len(unique)
            unique.append(item)
        elif key and item[2] > unique[positions[key]][2]:
            unique[positions[key]] = item

    if not unique:
        reasons = [
            "nenhum modelo comercial forte; marcas, categorias, genéricos e números foram excluídos"
        ]
        if unknown_numeric_removed:
            reasons = [
                "prefixo Unknown removido, mas sufixo numérico não possui evidência adicional"
            ]
        return {
            "record_id": record.record_id,
            "source_path": record.source_path,
            "original_text": record.original_model,
            "candidate": None,
            "cleaned_candidate": None,
            "confidence": 0.0,
            "extraction_source": None,
            "ambiguity": False,
            "alternatives": [],
            "reasons": reasons,
            "requires_review": True,
        }

    source, candidate, confidence, was_cleaned = unique[0]
    alternatives = [
        value for _, value, _, _ in unique[1:] if _normalized(value) != _normalized(candidate)
    ]
    if alternatives:
        confidence = min(confidence, 0.55)
    reasons = [
        f"padrão alfanumérico comercial encontrado em {source}",
        f"confiança da fonte limitada a {confidence:.2f}",
    ]
    if was_cleaned:
        reasons.append("prefixo Unknown removido; sufixo plausível preservado")
    if record.original_brand and _normalized(candidate) == _normalized(record.original_brand):
        return {
            "record_id": record.record_id,
            "source_path": record.source_path,
            "original_text": record.original_model,
            "candidate": None,
            "cleaned_candidate": None,
            "confidence": 0.0,
            "extraction_source": None,
            "ambiguity": True,
            "alternatives": [],
            "reasons": ["marca e modelo são iguais; candidato descartado"],
            "requires_review": True,
        }
    return {
        "record_id": record.record_id,
        "source_path": record.source_path,
        "original_text": record.original_model,
        "candidate": candidate,
        "cleaned_candidate": candidate if was_cleaned else None,
        "confidence": round(confidence, 4),
        "extraction_source": source,
        "ambiguity": bool(alternatives),
        "alternatives": sorted(set(alternatives)),
        "reasons": reasons,
        "requires_review": confidence < 0.8 or bool(alternatives),
    }
