"""Aliases explícitos de comandos para Capability IDs."""

import re
import unicodedata

ALIASES = {
    "power": "power",
    "on": "power_on",
    "power on": "power_on",
    "off": "power_off",
    "power off": "power_off",
    "power toggle": "power_toggle",
    "vol+": "volume_up",
    "volume+": "volume_up",
    "vol up": "volume_up",
    "volume up": "volume_up",
    "volume_up": "volume_up",
    "vol-": "volume_down",
    "volume-": "volume_down",
    "vol down": "volume_down",
    "volume down": "volume_down",
    "volume_down": "volume_down",
    "mute": "mute",
    "ch+": "channel_up",
    "channel up": "channel_up",
    "canal+": "channel_up",
    "ch-": "channel_down",
    "channel down": "channel_down",
    "canal-": "channel_down",
    "input": "input",
    "source": "input",
    "menu": "menu",
    "home": "home",
    "back": "back",
    "return": "back",
    "up": "direction_up",
    "down": "direction_down",
    "left": "direction_left",
    "right": "direction_right",
    "ok": "ok",
    "enter": "ok",
    "play": "play",
    "pause": "pause",
    "stop": "stop",
    "next": "next",
    "previous": "previous",
    "prev": "previous",
    "temp+": "temperature_up",
    "temperature up": "temperature_up",
    "temp-": "temperature_down",
    "temperature down": "temperature_down",
    "mode": "mode",
    "fan": "fan_speed",
    "fan speed": "fan_speed",
    "swing": "swing",
    "timer": "timer",
    "sleep": "sleep",
    "turbo": "turbo",
    "eco": "eco",
}

AMBIGUOUS = {"up", "down", "left", "right", "plus", "minus", "mode1"}


def normalize_command(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    value = re.sub(r"[\s_-]+", " ", value)
    return value


def numbered_pattern(value: str) -> tuple[str | None, int | None]:
    match = re.fullmatch(r"(.+?)[ _-]?(\d{1,5})", value.strip())
    if not match:
        return None, None
    return match.group(1).strip(), int(match.group(2))


def suggest_command(original: str, source_path: str) -> dict:
    key = normalize_command(original)
    base, number = numbered_pattern(original)
    reasons = []
    canonical = ALIASES.get(key)
    confidence = 0.99 if canonical else 0.0
    rule = "exact_alias" if canonical else "unresolved"
    ambiguous = key in AMBIGUOUS

    if base is not None:
        base_key = normalize_command(base)
        base_canonical = ALIASES.get(base_key)
        if base_canonical:
            canonical = base_canonical
            confidence = 0.58
            rule = "numbered_alias"
            ambiguous = True
            reasons.append(f"sufixo numérico detectado: {number}")
    if key in AMBIGUOUS:
        confidence = min(confidence, 0.55)
        reasons.append("nome depende do contexto do controle")

    if canonical:
        reasons.append(f"alias versionado corresponde a {canonical}")
    else:
        reasons.append("nenhum alias seguro corresponde ao nome")

    return {
        "original": original,
        "canonical_name": canonical if confidence >= 0.4 else None,
        "confidence": confidence,
        "rule": rule,
        "reasons": reasons,
        "evidence": [{"source": "command_name", "value": original, "path": source_path}],
        "ambiguity": ambiguous,
        "requires_review": ambiguous or confidence < 0.8,
    }
