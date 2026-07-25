"""Regras silver de alta precisão, independentes do classificador."""

import re
import unicodedata
from collections import Counter
from pathlib import PurePosixPath

REFERENCE_CLASSES = (
    "malformed",
    "universal_remote",
    "brute_force",
    "specific_device",
    "device_family",
    "test_or_sample",
)

GENERIC_MARKERS = re.compile(
    r"(?:^|[_\s-])(unknown|generic|universal|remote|brute(?:_?force)?|codeset|"
    r"all[_\s-]?models?)(?:$|[_\s-])",
    re.IGNORECASE,
)
UNIVERSAL_MARKERS = re.compile(
    r"(?:universal(?:[_\s-]+remote)?|all[_\s-]+models|multi[_\s-]+brand)",
    re.IGNORECASE,
)
BRUTE_MARKERS = re.compile(r"(?:brute[_\s-]*force|bruteforce|codeset|code[_\s-]*set)", re.I)
TEST_SEGMENT = re.compile(r"^(?:tests?|samples?|examples?|fixtures?|demos?)$", re.I)
MODEL_TOKEN = re.compile(r"^(?=.{3,60}$)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9][A-Za-z0-9._+,-]*$")
NON_CATEGORY_ROOTS = {"_converted_", "converted", "misc", "miscellaneous", "unknown"}
GENERIC_SUFFIXES = {
    "ac",
    "air_conditioner",
    "fan",
    "projector",
    "receiver",
    "soundbar",
    "tv",
    "television",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def numbered_sequences(names: list[str]) -> list[dict]:
    groups: dict[str, set[int]] = {}
    for name in names:
        match = re.fullmatch(r"\s*(.+?)[ _-]?(\d{1,5})\s*", name)
        if match:
            groups.setdefault(normalize(match.group(1)), set()).add(int(match.group(2)))
    result = []
    for base, values in sorted(groups.items()):
        ordered = sorted(values)
        if len(ordered) >= 3:
            span = ordered[-1] - ordered[0] + 1
            result.append(
                {
                    "base": base,
                    "count": len(ordered),
                    "first": ordered[0],
                    "last": ordered[-1],
                    "density": round(len(ordered) / span, 4),
                }
            )
    return result


def extensive_attempt_sequences(names: list[str]) -> list[dict]:
    """Retém apenas sequências inequívocas de tentativa do mesmo comando."""
    return [
        item
        for item in numbered_sequences(names)
        if item["base"] in {"power", "power_on", "power_off"}
        and item["count"] >= 8
        and item["density"] >= 0.7
    ]


def _simple_identity(record: dict) -> tuple[str, str, str] | None:
    path = PurePosixPath(record["relative_path"].replace("\\", "/"))
    parts = path.parts
    if len(parts) < 3 or normalize(parts[0]) in NON_CATEGORY_ROOTS:
        return None
    category, brand, filename = parts[0], parts[1], path.stem
    if normalize(brand) in {"unknown", "generic", "misc", "universal"}:
        return None
    return category, brand, filename


def _specific_reference(record: dict) -> dict | None:
    identity = _simple_identity(record)
    if not identity or record.get("issues"):
        return None
    category, brand, filename = identity
    if GENERIC_MARKERS.search(filename):
        return None
    brand_key = normalize(brand)
    filename_key = normalize(filename)
    if not filename_key.startswith(brand_key + "_"):
        return None
    suffix = filename[len(brand) :].lstrip(" _-")
    tokens = re.split(r"[\s/]+", suffix)
    commercial = next((token for token in tokens if MODEL_TOKEN.fullmatch(token)), None)
    if not commercial or record.get("signal_count", 0) < 1:
        return None
    if len(numbered_sequences(record.get("command_names", []))) > 0:
        return None
    return {
        "expected_classification": "specific_device",
        "reference_rule_id": "specific.brand_model_filename.v1",
        "reference_evidence": {
            "category_segment": category,
            "brand_segment": brand,
            "commercial_model": commercial,
            "filename": filename,
        },
    }


def _family_reference(record: dict) -> dict | None:
    identity = _simple_identity(record)
    if not identity or record.get("issues") or record.get("signal_count", 0) < 1:
        return None
    category, brand, filename = identity
    if GENERIC_MARKERS.search(filename):
        return None
    brand_key = normalize(brand)
    filename_key = normalize(filename)
    suffix = filename_key.removeprefix(brand_key).strip("_")
    if filename_key != brand_key and suffix not in GENERIC_SUFFIXES:
        return None
    return {
        "expected_classification": "device_family",
        "reference_rule_id": "family.brand_without_model.v1",
        "reference_evidence": {
            "category_segment": category,
            "brand_segment": brand,
            "filename": filename,
            "model_absent": True,
        },
    }


def derive_reference(record: dict, parse_error_paths: set[str]) -> dict | None:
    """Deriva um único label sem consultar classificação ou confiança previstas."""
    path = record["relative_path"].replace("\\", "/")
    path_object = PurePosixPath(path)
    path_text = path.replace("/", " ")
    names = record.get("command_names", [])
    sequences = numbered_sequences(names)

    if path in parse_error_paths or record.get("issues"):
        return {
            "expected_classification": "malformed",
            "reference_rule_id": "malformed.inventory_parse_error.v1",
            "reference_evidence": {
                "parse_error_reported": path in parse_error_paths,
                "inventory_issues": record.get("issues", []),
            },
        }

    test_segments = [part for part in path_object.parts if TEST_SEGMENT.fullmatch(part)]
    if test_segments:
        return {
            "expected_classification": "test_or_sample",
            "reference_rule_id": "sample.explicit_path_segment.v1",
            "reference_evidence": {"explicit_segments": test_segments},
        }

    dedicated_universal = path_object.parts and path_object.parts[0].casefold() == (
        "Universal_TV_Remotes".casefold()
    )
    special_function = re.search(r"(?:region[_\s-]*unlock|service[_\s-]*menu)", path, re.I)
    explicit_universal = UNIVERSAL_MARKERS.search(path_text)
    if (dedicated_universal or explicit_universal) and not special_function:
        return {
            "expected_classification": "universal_remote",
            "reference_rule_id": (
                "universal.dedicated_directory.v1"
                if dedicated_universal
                else "universal.explicit_marker.v1"
            ),
            "reference_evidence": {
                "dedicated_directory": dedicated_universal,
                "explicit_marker": explicit_universal.group(0) if explicit_universal else None,
            },
        }

    extensive = extensive_attempt_sequences(names)
    brute_marker = BRUTE_MARKERS.search(path_text)
    confirmed_marker = brute_marker and (
        any(item["count"] >= 3 for item in sequences) or record.get("signal_count", 0) >= 50
    )
    if extensive or confirmed_marker:
        return {
            "expected_classification": "brute_force",
            "reference_rule_id": (
                "brute.extensive_numbered_intent.v1"
                if extensive
                else "brute.marker_confirmed_by_content.v1"
            ),
            "reference_evidence": {
                "sequences": extensive or sequences,
                "marker": brute_marker.group(0) if confirmed_marker else None,
                "signal_count": record.get("signal_count", 0),
            },
        }

    return _specific_reference(record) or _family_reference(record)


def rule_counts(rows: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(row["reference_rule_id"] for row in rows).items()))
