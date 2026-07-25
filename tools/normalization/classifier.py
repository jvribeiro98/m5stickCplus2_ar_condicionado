"""Classificação conservadora, contextual e explicável de arquivos."""

import re
from collections import Counter

from .commands import normalize_command, suggest_command
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
UNIVERSAL_MARKERS = (
    "universal",
    "universal remote",
    "codeset",
    "code set",
    "all models",
    "multi brand",
)
STRONG_GROUP_PATTERNS = {
    "climate": (
        "temperature_up",
        "temperature_down",
        "temp_up",
        "temp_down",
        "swing_vertical",
        "swing_horizontal",
        "fan_speed",
    ),
    "television": ("channel_up", "channel_down", "subtitle", "program_guide"),
    "audio": (
        "subwoofer_up",
        "subwoofer_down",
        "bass_up",
        "bass_down",
        "treble_up",
        "treble_down",
    ),
    "fan": ("oscillation", "breeze"),
    "lighting": (
        "brightness_up",
        "brightness_down",
        "strobe",
        "color_red",
        "color_blue",
    ),
    "media": ("play", "pause", "stop", "rewind", "fast_forward", "next", "previous"),
}
CATEGORY_GROUPS = {
    "projector": {"media", "lighting", "television"},
    "tv": {"media", "television", "audio", "lighting"},
    "air_conditioner": {"climate", "fan"},
    "fan": {"fan", "climate", "lighting"},
    "receiver": {"audio", "media", "television", "lighting"},
    "soundbar": {"audio", "media", "television"},
    "led_strip": {"lighting", "media", "climate"},
    "media_player": {"media", "television"},
    "dvd_player": {"media", "television"},
    "blu_ray_player": {"media", "television"},
}
INCOMPATIBLE_GROUP_PAIRS = {
    frozenset(("climate", "television")),
    frozenset(("climate", "media")),
    frozenset(("climate", "audio")),
    frozenset(("fan", "television")),
    frozenset(("fan", "media")),
}


def _numbered(command_names: list[str]) -> list[tuple[str, int]]:
    result = []
    for name in command_names:
        match = re.fullmatch(r"(.+?)[ _-]?(\d{1,5})", name.strip())
        if match:
            result.append((match.group(1).strip().casefold(), int(match.group(2))))
    return result


def _strong_semantics(command_names: list[str], path: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for original in command_names:
        suggestion = suggest_command(original, path)
        canonical = suggestion["canonical_name"] or ""
        normalized = normalize_command(original).replace(" ", "_")
        values = {canonical, normalized}
        for group, patterns in STRONG_GROUP_PATTERNS.items():
            if any(
                value == pattern or value.startswith(pattern + "_")
                for value in values
                for pattern in patterns
            ):
                matches.setdefault(group, []).append(original)
    return {group: sorted(set(commands)) for group, commands in sorted(matches.items())}


def classify(
    record: InventoryRecord,
    model_candidate: dict,
    category_suggestion: dict | None = None,
    brand_suggestion: dict | None = None,
) -> dict:
    path_key = record.source_path.replace("\\", "/").casefold()
    normalized_path = re.sub(r"[_\s-]+", " ", path_key)
    names = [command.original_name for command in record.commands]
    numbered = _numbered(names)
    base_counts = Counter(base for base, _ in numbered)
    protocols = {command.protocol for command in record.commands if command.protocol}
    addresses = {command.address for command in record.commands if command.address}
    signal_count = max(record.signal_count, len(record.commands))
    strong_semantics = _strong_semantics(names, record.source_path)

    scores = {name: 0.0 for name in CLASSES}
    reasons = {name: [] for name in CLASSES}

    if record.parse_errors:
        scores["malformed"] = 0.9
        reasons["malformed"].append(f"{len(record.parse_errors)} problema(s) de parsing")
    if any(token in path_key for token in ("/test", "/sample", "example", "/demo")):
        scores["test_or_sample"] = 0.86
        reasons["test_or_sample"].append("caminho contém marcador explícito de teste")

    explicit_generic = [
        word for word in GENERIC_PATH_WORDS if word.replace("_", " ") in normalized_path
    ]
    if explicit_generic:
        scores["brute_force"] += 0.28
        reasons["brute_force"].append(
            "marcador genérico no caminho: " + ", ".join(explicit_generic)
        )

    matched_universal = sorted(marker for marker in UNIVERSAL_MARKERS if marker in normalized_path)
    if matched_universal:
        scores["universal_remote"] = 0.82
        reasons["universal_remote"].append(
            "indicador explícito de universalidade: " + ", ".join(matched_universal)
        )
    if any(token in path_key for token in ("/misc", "/mixed", "collection")):
        scores["mixed_collection"] += 0.42
        reasons["mixed_collection"].append("metadado/caminho sugere coleção mista")

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

    resolved_category = category_suggestion["normalized_value"] if category_suggestion else None
    semantic_category = resolved_category if resolved_category in CATEGORY_GROUPS else None
    allowed_groups = CATEGORY_GROUPS.get(semantic_category, set())
    incompatible = {
        group: commands
        for group, commands in strong_semantics.items()
        if semantic_category and group not in allowed_groups
    }
    if semantic_category and incompatible:
        scores["mixed_collection"] += 0.74
        details = "; ".join(
            f"{group}: {', '.join(commands[:6])}"
            for group, commands in sorted(incompatible.items())
        )
        reasons["mixed_collection"].append(
            f"comandos fortes incompatíveis com {semantic_category}: {details}"
        )
    unresolved_conflicts = [
        pair for pair in INCOMPATIBLE_GROUP_PAIRS if pair.issubset(strong_semantics)
    ]
    if not semantic_category and unresolved_conflicts:
        scores["mixed_collection"] += 0.7
        reasons["mixed_collection"].append(
            "grupos fortes incompatíveis sem categoria resolvida: "
            + "; ".join(
                "+".join(sorted(pair))
                for pair in sorted(unresolved_conflicts, key=lambda item: sorted(item))
            )
        )
    if len(incompatible) >= 2 or (not semantic_category and len(unresolved_conflicts) >= 2):
        scores["mixed_collection"] += 0.16
        reasons["mixed_collection"].append("múltiplos grupos semanticamente incompatíveis")
    if len(protocols) >= 4 and len(addresses) >= 8 and (incompatible or "/mixed" in path_key):
        scores["mixed_collection"] += 0.22
        reasons["mixed_collection"].append("alta diversidade técnica confirma coleção mista")

    model_confidence = model_candidate["confidence"]
    if category_suggestion is None:
        category_confidence = record.category_confidence
    elif resolved_category is not None:
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
    technical_coherence = (
        1 <= signal_count <= 80 and 1 <= len(protocols) <= 2 and len(addresses) <= 4
    )
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
    elif brand_confidence >= 0.6 and category_confidence >= 0.65:
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
        if 1 <= len(protocols) <= 2:
            scores["device_family"] += 0.05
            reasons["device_family"].append(
                f"dados técnicos observados em {len(protocols)} protocolo(s)"
            )
        elif not protocols:
            reasons["device_family"].append("dados técnicos insuficientes")

    if matched_universal and model_confidence >= 0.65 and signal_count <= 20:
        scores["device_family"] = max(scores["device_family"], 0.74)
        reasons["device_family"].append(
            "modelo plausível e conjunto pequeno conflitam com marcador universal"
        )
        reasons["universal_remote"].append("modelo plausível exige revisão do marcador universal")
    if matched_universal and (sequential_groups or signal_count >= 24 or len(addresses) >= 4):
        scores["universal_remote"] += 0.08
        reasons["universal_remote"].append("volume/diversidade reforça o indicador universal")
        if sequential_groups:
            reasons["universal_remote"].append(
                f"{sequential_count} comandos numerados reforçam a estrutura universal"
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
            "strong_semantics": strong_semantics,
            "incompatible_semantic_groups": sorted(incompatible),
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
