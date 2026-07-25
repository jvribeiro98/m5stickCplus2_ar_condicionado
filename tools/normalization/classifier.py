"""Classificação explicável de arquivos inventariados."""

import re
from collections import Counter

from .confidence import clamp
from .models import InventoryRecord

CLASSES = (
    "specific_device",
    "device_family",
    "universal_remote",
    "brute_force",
    "mixed_collection",
    "test_or_sample",
    "malformed",
    "unknown",
)


def _numbered(command_names: list[str]) -> list[tuple[str, int]]:
    result = []
    for name in command_names:
        match = re.fullmatch(r"(.+?)[ _-]?(\d{1,5})", name.strip())
        if match:
            result.append((match.group(1).strip().casefold(), int(match.group(2))))
    return result


def classify(record: InventoryRecord, model_candidate: dict) -> dict:
    path_key = record.source_path.replace("\\", "/").casefold()
    names = [command.original_name for command in record.commands]
    numbered = _numbered(names)
    base_counts = Counter(base for base, _ in numbered)
    protocols = {command.protocol for command in record.commands if command.protocol}
    addresses = {command.address for command in record.commands if command.address}
    signal_count = max(record.signal_count, len(record.commands))

    scores = {name: 0.0 for name in CLASSES}
    reasons = {name: [] for name in CLASSES}

    if record.parse_errors:
        scores["malformed"] += 0.95
        reasons["malformed"].append(f"{len(record.parse_errors)} erro(s) de parsing")
    if any(token in path_key for token in ("/test", "/sample", "example", "demo")):
        scores["test_or_sample"] += 0.86
        reasons["test_or_sample"].append("caminho contém marcador de teste ou amostra")
    if any(token in path_key for token in ("brute", "codeset")):
        scores["brute_force"] += 0.35
        reasons["brute_force"].append("caminho contém brute ou codeset")
    if "universal" in path_key:
        scores["universal_remote"] += 0.35
        reasons["universal_remote"].append("caminho contém universal")
    if any(token in path_key for token in ("/misc", "/mixed", "collection")):
        scores["mixed_collection"] += 0.28
        reasons["mixed_collection"].append("caminho sugere coleção mista")

    repeated_numbered = sum(count for count in base_counts.values() if count >= 3)
    if repeated_numbered >= 3:
        contribution = min(0.42, 0.18 + repeated_numbered / 300)
        scores["brute_force"] += contribution
        reasons["brute_force"].append(
            f"{repeated_numbered} comandos numerados repetem a mesma intenção"
        )
    if signal_count >= 64:
        scores["brute_force"] += 0.18
        reasons["brute_force"].append(f"grande quantidade de sinais: {signal_count}")
    if len(protocols) >= 4:
        scores["mixed_collection"] += 0.28
        scores["brute_force"] += 0.12
        reasons["mixed_collection"].append(f"diversidade de protocolos: {len(protocols)}")
        reasons["brute_force"].append(f"múltiplos protocolos: {len(protocols)}")
    if len(addresses) >= 8:
        scores["brute_force"] += 0.18
        reasons["brute_force"].append(f"diversidade de endereços: {len(addresses)}")
    if record.duplicate_count >= 8:
        scores["universal_remote"] += 0.08
        scores["device_family"] += 0.06
        reasons["universal_remote"].append(
            f"{record.duplicate_count} sinais idênticos aparecem em outros arquivos"
        )
        reasons["device_family"].append(
            f"{record.duplicate_count} sinais compartilhados sugerem família"
        )

    if model_candidate["candidate"]:
        if signal_count and signal_count <= 80 and len(protocols) <= 3:
            scores["specific_device"] += 0.72
            reasons["specific_device"].append("modelo identificável e conjunto coerente")
        else:
            scores["device_family"] += 0.58
            reasons["device_family"].append("modelo/família identificável com conjunto amplo")
    else:
        reasons["brute_force"].append("nenhum modelo identificável")

    if scores["universal_remote"] and (
        repeated_numbered >= 3 or signal_count >= 32 or len(protocols) >= 3
    ):
        scores["universal_remote"] += 0.38
        reasons["universal_remote"].append("estrutura ampla confirma indicador do caminho")
        if repeated_numbered:
            reasons["universal_remote"].append(
                f"{repeated_numbered} comandos numerados reforçam o conjunto universal"
            )
    if scores["mixed_collection"] and len(protocols) >= 2:
        scores["mixed_collection"] += 0.32
        reasons["mixed_collection"].append("diversidade técnica confirma coleção mista")

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    classification, score = ranked[0]
    if score < 0.4:
        classification = "unknown"
        score = max(0.2, score)
        reasons["unknown"].append("evidências insuficientes para classificação segura")

    conflicts = [
        {"classification": name, "score": clamp(value)}
        for name, value in ranked[1:]
        if value >= 0.4 and score - value < 0.2
    ]
    return {
        "record_id": record.record_id,
        "source_path": record.source_path,
        "classification": classification,
        "confidence": clamp(score),
        "reasons": sorted(set(reasons[classification])),
        "conflicts": conflicts,
        "requires_review": bool(conflicts) or score < 0.8,
        "evidence": {
            "signal_count": signal_count,
            "numbered_command_count": len(numbered),
            "protocol_count": len(protocols),
            "address_count": len(addresses),
            "duplicate_count": record.duplicate_count,
            "model_candidate": model_candidate["candidate"],
        },
        "original": {
            "category": record.original_category,
            "brand": record.original_brand,
            "model": record.original_model,
            "command_names": names,
        },
    }
