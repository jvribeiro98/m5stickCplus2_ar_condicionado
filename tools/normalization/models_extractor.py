"""Extração conservadora de candidatos de modelo."""

import re
from pathlib import PurePosixPath

from .models import InventoryRecord

GENERIC = {
    "remote",
    "control",
    "controller",
    "universal",
    "codes",
    "code",
    "brute",
    "bruteforce",
    "sample",
    "test",
    "misc",
    "unknown",
}
MODEL_TOKEN = re.compile(r"(?i)^(?=.{3,40}$)(?=.*[a-z])(?=.*\d)[a-z0-9][a-z0-9._-]*$")


def _tokens(text: str) -> list[str]:
    return [token for token in re.split(r"[\s/\\]+", text) if token]


def extract_model(record: InventoryRecord) -> dict:
    if record.original_model and record.original_model.strip():
        value = record.original_model.strip()
        return {
            "record_id": record.record_id,
            "source_path": record.source_path,
            "original_text": record.original_model,
            "candidate": value,
            "confidence": 0.98,
            "extraction_source": "inventory.model",
            "ambiguity": False,
            "alternatives": [],
            "reasons": ["campo de modelo explícito no inventário"],
            "requires_review": False,
        }

    path = PurePosixPath(record.source_path.replace("\\", "/"))
    sources = [
        ("file_name", path.stem),
        ("parent_directory", path.parent.name),
        *[("comment", comment) for comment in record.comments],
    ]
    candidates: list[tuple[str, str]] = []
    for source, text in sources:
        for token in _tokens(text):
            clean = token.strip("()[]{}.,")
            if clean.casefold() not in GENERIC and MODEL_TOKEN.fullmatch(clean):
                candidates.append((source, clean))

    unique = []
    for item in candidates:
        if item[1].casefold() not in {candidate.casefold() for _, candidate in unique}:
            unique.append(item)

    if not unique:
        return {
            "record_id": record.record_id,
            "source_path": record.source_path,
            "original_text": None,
            "candidate": None,
            "confidence": 0.0,
            "extraction_source": None,
            "ambiguity": True,
            "alternatives": [],
            "reasons": ["nenhum padrão alfanumérico claro foi encontrado"],
            "requires_review": True,
        }

    source, candidate = unique[0]
    alternatives = [value for _, value in unique[1:]]
    confidence = 0.84 if source == "file_name" and not alternatives else 0.62
    return {
        "record_id": record.record_id,
        "source_path": record.source_path,
        "original_text": path.stem if source == "file_name" else path.parent.name,
        "candidate": candidate,
        "confidence": confidence,
        "extraction_source": source,
        "ambiguity": bool(alternatives),
        "alternatives": alternatives,
        "reasons": [
            f"token alfanumérico com letras e números encontrado em {source}",
            *([f"alternativas encontradas: {', '.join(alternatives)}"] if alternatives else []),
        ],
        "requires_review": bool(alternatives) or confidence < 0.8,
    }
