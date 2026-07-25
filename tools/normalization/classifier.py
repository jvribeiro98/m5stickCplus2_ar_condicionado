"""Classificação conservadora, pontuada e explicável de arquivos."""

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

GENERIC_PATH_WORDS = ("brute", "bruteforce", "universal", "codeset", "database")
CLIMATE_WORDS = ("temp", "temperature", "cool", "heat", "swing", "fan_speed")
MEDIA_WORDS = ("play", "pause", "stop", "channel", "subtitle", "rewind", "input")
LIGHT_WORDS = ("brightness", "dimmer", "color", "rgb", "white", "strobe")


def _numbered(command_names: list[str]) -> list[tuple[str, int]]:
    result = []
    for name in command_names:
        match = re.fullmatch(r"(.+?)[ _-]?(\d{1,5})", name.strip())
        if match:
            result.append((match.group(1).strip().casefold(), int(match.group(2))))
    return result


def _semantic_groups(command_names: list[str]) -> set[str]:
    joined = " ".join(command_names).casefold()
    groups = set()
    if any(word in joined for word in CLIMATE_WORDS):
        groups.add("climate")
    if any(word in joined for word in MEDIA_WORDS):
        groups.add("media")
    if any(word in joined for word in LIGHT_WORDS):
        groups.add("lighting")
    return groups


def classify(
    record: InventoryRecord,
    model_candidate: dict,
    category_suggestion: dict | None = None,
    brand_suggestion: dict | None = None,
) -> dict:
    path_key = record.source_path.replace("\\", "/").casefold()
    names = [command.original_name for command in record.commands]
    numbered = _numbered(names)
    base_counts = Counter(base for base, _ in numbered)
    protocols = {command.protocol for command in record.commands if command.protocol}
    addresses = {command.address for command in record.commands if command.address}
    signal_count = max(record.signal_count, len(record.commands))
    semantic_groups = _semantic_groups(names)

    scores = {name: 0.0 for name in CLASSES}
    reasons = {name: [] for name in CLASSES}

    if record.parse_errors:
        scores["malformed"] = 0.9
        reasons["malformed"].append(f"{len(record.parse_errors)} problema(s) de parsing")
    if any(token in path_key for token in ("/test", "/sample", "example", "/demo")):
        scores["test_or_sample"] = 0.86
        reasons["test_or_sample"].append("caminho contém marcador explícito de teste")

    explicit_generic = [word for word in GENERIC_PATH_WORDS if word in path_key]
    if explicit_generic:
        scores["brute_force"] += 0.28
        reasons["brute_force"].append(
            "marcador genérico no caminho: " + ", ".join(explicit_generic)
        )
    if "universal" in path_key:
        scores["universal_remote"] += 0.48
        reasons["universal_remote"].append("caminho declara controle universal")
    if "codeset" in path_key or "database" in path_key:
        scores["universal_remote"] += 0.28
        reasons["universal_remote"].append("estrutura declara codeset/database")
    if any(token in path_key for token in ("/misc", "/mixed", "collection")):
        scores["mixed_collection"] += 0.24
        reasons["mixed_collection"].append("caminho sugere coleção mista")

    sequential_groups = [
        (base, sorted({number for candidate, number in numbered if candidate == base}))
        for base, count in base_counts.items()
        if count >= 3
    ]
    sequential_count = sum(len(numbers) for _, numbers in sequential_groups)
    if sequential_groups:
        scores["brute_force"] += min(0.52, 0.3 + sequential_count / 500)
        preview = ", ".join(f"{base} ({len(numbers)})" for base, numbers in sequential_groups[:3])
        reasons["brute_force"].append(f"sequências numeradas por intenção: {preview}")

    raw_prefix_counts = Counter(
        re.sub(r"[^a-z]+", "", name.casefold())[:8] for name in names if name
    )
    dominant_prefix_count = max(raw_prefix_counts.values(), default=0)
    if dominant_prefix_count >= 12:
        scores["brute_force"] += min(0.25, dominant_prefix_count / 300)
        reasons["brute_force"].append(
            f"{dominant_prefix_count} comandos compartilham prefixo textual"
        )
    if signal_count >= 100:
        scores["brute_force"] += min(0.18, signal_count / 2000)
        reasons["brute_force"].append(f"conjunto muito grande: {signal_count} sinais")
    if len(protocols) >= 3:
        scores["brute_force"] += min(0.18, len(protocols) / 40)
        scores["universal_remote"] += min(0.18, len(protocols) / 40)
        reasons["brute_force"].append(f"diversidade de protocolos: {len(protocols)}")
        reasons["universal_remote"].append(f"diversidade de protocolos: {len(protocols)}")
    if len(addresses) >= 8:
        scores["brute_force"] += min(0.2, len(addresses) / 100)
        scores["universal_remote"] += min(0.22, len(addresses) / 100)
        reasons["brute_force"].append(f"diversidade de endereços: {len(addresses)}")
        reasons["universal_remote"].append(f"diversidade de endereços: {len(addresses)}")
    if not model_candidate["candidate"]:
        scores["brute_force"] += 0.06
        scores["universal_remote"] += 0.06
        reasons["brute_force"].append("nenhum modelo confiável")
        reasons["universal_remote"].append("nenhum modelo específico")

    if {"climate", "media"} <= semantic_groups:
        scores["mixed_collection"] += 0.52
        reasons["mixed_collection"].append(
            "comandos de climatização e mídia coexistem no mesmo arquivo"
        )
    if len(semantic_groups) >= 3:
        scores["mixed_collection"] += 0.2
        reasons["mixed_collection"].append(
            "três grupos semânticos distintos: " + ", ".join(sorted(semantic_groups))
        )
    if len(protocols) >= 4 and len(addresses) >= 8:
        scores["mixed_collection"] += 0.22
        reasons["mixed_collection"].append("alta diversidade conjunta de protocolos e endereços")

    model_confidence = model_candidate["confidence"]
    if category_suggestion is None:
        category_confidence = record.category_confidence
    elif category_suggestion["normalized_value"] is not None:
        category_confidence = category_suggestion["confidence"]
    else:
        category_confidence = 0.0
    brand_confidence = (
        brand_suggestion["confidence"]
        if brand_suggestion and brand_suggestion["suggested_brand_id"] is not None
        else record.brand_confidence
    )
    identity_strong = (
        brand_confidence >= 0.6 and category_confidence >= 0.65 and model_confidence >= 0.65
    )
    technical_coherence = 1 <= signal_count <= 80 and len(protocols) <= 2 and len(addresses) <= 4
    strong_non_device = max(
        scores["brute_force"],
        scores["universal_remote"],
        scores["mixed_collection"],
    )
    if identity_strong and technical_coherence and strong_non_device < 0.55:
        scores["specific_device"] = 0.58
        scores["specific_device"] += min(0.1, brand_confidence / 10)
        scores["specific_device"] += min(0.1, category_confidence / 10)
        scores["specific_device"] += min(0.1, model_confidence / 10)
        if names:
            scores["specific_device"] += 0.05
            reasons["specific_device"].append(
                f"conjunto interno coerente com {len(names)} comandos"
            )
        reasons["specific_device"].extend(
            [
                f"marca com confiança {brand_confidence:.2f}",
                f"categoria normalizada com confiança {category_confidence:.2f}",
                f"modelo conservador com confiança {model_confidence:.2f}",
            ]
        )
    else:
        if brand_confidence >= 0.6 and category_confidence >= 0.65:
            scores["device_family"] = 0.48
            if signal_count <= 200:
                scores["device_family"] += 0.08
            if model_candidate["candidate"]:
                scores["device_family"] += 0.06
                reasons["device_family"].append(
                    f"modelo provável, mas confiança limitada a {model_confidence:.2f}"
                )
            else:
                reasons["device_family"].append(
                    "marca e categoria conhecidas, sem modelo específico confiável"
                )
            if len(protocols) <= 2:
                scores["device_family"] += 0.05
                reasons["device_family"].append("protocolos tecnicamente coerentes")

    if "universal" in path_key and (sequential_groups or signal_count >= 24 or len(addresses) >= 4):
        scores["universal_remote"] += 0.22
        reasons["universal_remote"].append("volume/diversidade confirma o indicador universal")
        if sequential_groups:
            reasons["universal_remote"].append(
                f"{sequential_count} comandos numerados reforçam a estrutura universal"
            )
    if scores["mixed_collection"] and len(protocols) >= 3:
        scores["mixed_collection"] += 0.3
        reasons["mixed_collection"].append(
            f"{len(protocols)} protocolos confirmam coleção tecnicamente mista"
        )

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    classification, score = ranked[0]
    if score < 0.4:
        classification = "unknown"
        score = 0.35 if names or signal_count else 0.2
        reasons["unknown"].append(
            "identidade ou evidência técnica insuficiente para classe mais específica"
        )

    conflicts = [
        {"classification": name, "score": clamp(value)}
        for name, value in ranked
        if name != classification and value >= 0.4 and score - value < 0.12
    ]
    return {
        "record_id": record.record_id,
        "source_path": record.source_path,
        "classification": classification,
        "confidence": clamp(score),
        "reasons": sorted(set(reasons[classification])),
        "conflicts": conflicts,
        "requires_review": bool(conflicts) or score < 0.72,
        "evidence": {
            "signal_count": signal_count,
            "numbered_command_count": len(numbered),
            "sequential_group_count": len(sequential_groups),
            "dominant_prefix_count": dominant_prefix_count,
            "protocol_count": len(protocols),
            "address_count": len(addresses),
            "semantic_groups": sorted(semantic_groups),
            "model_candidate": model_candidate["candidate"],
            "model_confidence": model_confidence,
            "brand_confidence": brand_confidence,
            "category_confidence": category_confidence,
            "duplicate_count": record.duplicate_count,
        },
        "original": {
            "category": record.original_category,
            "brand": record.original_brand,
            "model": record.original_model,
            "command_names": names,
        },
    }
