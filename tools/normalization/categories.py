"""Taxonomia e regras explícitas de categoria."""

import re

from .confidence import clamp

CATEGORY_ALIASES = {
    "tv": "tv",
    "television": "tv",
    "televisions": "tv",
    "tvs": "tv",
    "air conditioner": "air_conditioner",
    "air_conditioner": "air_conditioner",
    "air conditioners": "air_conditioner",
    "ac": "air_conditioner",
    "acs": "air_conditioner",
    "air purifiers": "air_purifier",
    "audio and video receivers": "receiver",
    "blu ray": "blu_ray_player",
    "cable boxes": "set_top_box",
    "cameras": "camera",
    "consoles": "game_console",
    "dvd players": "dvd_player",
    "heaters": "heater",
    "humidifiers": "humidifier",
    "led lighting": "led_strip",
    "streaming devices": "media_player",
    "tv tuner": "media_player",
    "universal tv remotes": "tv",
    "fan": "fan",
    "fans": "fan",
    "projector": "projector",
    "projectors": "projector",
    "receiver": "receiver",
    "receivers": "receiver",
    "avr": "receiver",
    "soundbar": "soundbar",
    "soundbars": "soundbar",
    "led": "led_strip",
    "led strip": "led_strip",
    "led_strip": "led_strip",
    "camera": "camera",
    "light": "light",
    "lights": "light",
    "media player": "media_player",
    "media_player": "media_player",
    "set top box": "set_top_box",
    "set_top_box": "set_top_box",
    "stb": "set_top_box",
    "dvd": "dvd_player",
    "dvd player": "dvd_player",
    "blu-ray": "blu_ray_player",
    "game console": "game_console",
    "heater": "heater",
    "humidifier": "humidifier",
    "air purifier": "air_purifier",
    "other": "other",
    "misc": "other",
    "unknown": "unknown",
}


def normalize_key(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value.strip().casefold().replace("-", " ").replace("_", " "),
    )


def suggest_category(original: str | None, path: str) -> dict:
    evidence = []
    if original:
        key = normalize_key(original)
        if key in CATEGORY_ALIASES:
            normalized = CATEGORY_ALIASES[key]
            return {
                "source_value": original,
                "normalized_value": normalized,
                "confidence": 0.99,
                "rule_type": "exact_alias",
                "examples": [path],
                "notes": "Correspondência explícita na taxonomia versionada.",
                "reasons": [f"alias exato: {original!r} -> {normalized!r}"],
            }
        evidence.append(f"categoria original não reconhecida: {original!r}")

    path_key = normalize_key(path.replace("\\", " ").replace("/", " "))
    matches = sorted(
        {
            normalized
            for alias, normalized in CATEGORY_ALIASES.items()
            if len(alias) > 2 and re.search(rf"\b{re.escape(alias)}\b", path_key)
        }
    )
    if len(matches) == 1:
        evidence.append(f"um único indicador de caminho: {matches[0]}")
        return {
            "source_value": original,
            "normalized_value": matches[0],
            "confidence": clamp(0.68 if original else 0.74),
            "rule_type": "path_evidence",
            "examples": [path],
            "notes": "Sugestão por caminho; exige revisão antes de aplicação.",
            "reasons": evidence,
        }
    if len(matches) > 1:
        evidence.append("indicadores conflitantes no caminho: " + ", ".join(matches))
    return {
        "source_value": original,
        "normalized_value": None,
        "confidence": 0.0,
        "rule_type": "unresolved",
        "examples": [path],
        "notes": "Nenhuma categoria foi aplicada silenciosamente.",
        "reasons": evidence or ["sem evidência de categoria"],
    }
