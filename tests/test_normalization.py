import hashlib
from pathlib import Path

from tools.normalization.brands import suggest_brand
from tools.normalization.categories import suggest_category
from tools.normalization.classifier import classify
from tools.normalization.commands import suggest_command
from tools.normalization.models import CommandRecord, InventoryRecord
from tools.normalization.models_extractor import extract_model
from tools.normalization.reports import analyze_reports, inspect_output, load_inventory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REPORTS = ROOT / "tests" / "fixtures" / "normalization"
REAL_FORMAT_FIXTURE = ROOT / "tests" / "fixtures" / "normalization-real"


def record(path: str, **kwargs) -> InventoryRecord:
    return InventoryRecord(
        record_id=kwargs.pop("record_id", "fixture"),
        source_path=path,
        original_category=kwargs.pop("category", None),
        original_brand=kwargs.pop("brand", None),
        original_model=kwargs.pop("model", None),
        **kwargs,
    )


def directory_digest(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def ir_digest() -> dict[str, str]:
    return {
        item.relative_to(ROOT).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(ROOT.rglob("*.ir"))
    }


def test_known_categories():
    result = suggest_category("Televisions", "TVs/Samsung/model.ir")
    assert result["normalized_value"] == "tv"
    assert result["confidence"] == 0.99


def test_safe_brand_alias():
    result = suggest_brand("SAMSUNG", "TVs/SAMSUNG/model.ir")
    assert result["suggested_brand_id"] == "samsung"
    assert result["display_name"] == "Samsung"
    assert result["original"] == "SAMSUNG"


def test_ambiguous_brand_is_not_applied():
    result = suggest_brand("Generic", "Universal/codes.ir")
    assert result["suggested_brand_id"] is None
    assert result["requires_review"]


def test_clear_model_extraction():
    result = extract_model(record("TVs/Samsung/KDL55X9000.ir"))
    assert result["candidate"] == "KDL55X9000"
    assert result["confidence"] >= 0.7


def test_missing_model_requires_review():
    result = extract_model(record("Misc/remote.ir"))
    assert result["candidate"] is None
    assert result["requires_review"]


def test_volume_plus_command():
    result = suggest_command("Volume+", "TV/example.ir")
    assert result["canonical_name"] == "volume_up"
    assert result["confidence"] >= 0.95


def test_volume_minus_real_alias():
    result = suggest_command("VOL-", "TV/example.ir")
    assert result["canonical_name"] == "volume_down"
    assert result["confidence"] >= 0.95


def test_power1_is_bruteforce_evidence_and_review_candidate():
    command = suggest_command("Power1", "Universal/power.ir")
    commands = tuple(CommandRecord(f"Power{i}", "NEC", f"0x{i:02X}") for i in range(1, 9))
    item = record("Universal/Power_Codes.ir", commands=commands, signal_count=128)
    model = extract_model(item)
    result = classify(item, model)

    assert command["canonical_name"] == "power"
    assert command["requires_review"]
    assert result["classification"] in {"brute_force", "universal_remote"}
    assert any("numer" in reason or "quantidade" in reason for reason in result["reasons"])


def test_specific_file():
    item = record(
        "TVs/Samsung/KDL55X9000.ir",
        brand="Samsung",
        category="TVs",
        brand_confidence=0.7,
        category_confidence=0.85,
        commands=(CommandRecord("Power", "NEC", "0x01"),),
    )
    result = classify(item, extract_model(item))
    assert result["classification"] == "specific_device"


def test_universal_file_uses_multiple_signals():
    commands = tuple(CommandRecord(f"Power{i}", "NEC", f"0x{i:02X}") for i in range(1, 9))
    item = record("Universal/TV/Power_Codes.ir", commands=commands, signal_count=64)
    result = classify(item, extract_model(item))
    assert result["classification"] == "universal_remote"
    assert len(result["reasons"]) >= 2


def test_mixed_file_uses_protocol_diversity():
    commands = tuple(
        CommandRecord(name, protocol, f"0x{index:02X}")
        for index, (name, protocol) in enumerate(
            (("A", "NEC"), ("B", "RC5"), ("C", "RC6"), ("D", "Sony"))
        )
    )
    item = record("Misc/Mixed/collection.ir", commands=commands)
    result = classify(item, extract_model(item))
    assert result["classification"] == "mixed_collection"


def test_confidence_is_deterministic():
    item = record("TVs/Samsung/KDL55X9000.ir", commands=(CommandRecord("Power"),))
    assert classify(item, extract_model(item)) == classify(item, extract_model(item))


def test_outputs_are_byte_identical(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    analyze_reports(FIXTURE_REPORTS, first)
    analyze_reports(FIXTURE_REPORTS, second)
    assert directory_digest(first) == directory_digest(second)


def test_original_values_are_preserved(tmp_path: Path):
    records, _ = load_inventory(FIXTURE_REPORTS)
    original = next(item for item in records if item.record_id == "specific-tv")
    output = tmp_path / "output"
    analyze_reports(FIXTURE_REPORTS, output)

    assert original.original_category == "Televisions"
    assert original.original_brand == "SAMSUNG"
    assert original.commands[1].original_name == "Volume+"
    assert "Televisions" in (output / "category-map.proposed.json").read_text(encoding="utf-8")
    assert "SAMSUNG" in (output / "brand-map.proposed.json").read_text(encoding="utf-8")
    assert "Volume+" in (output / "command-aliases.proposed.json").read_text(encoding="utf-8")


def test_no_ir_file_is_modified(tmp_path: Path):
    before = ir_digest()
    analyze_reports(FIXTURE_REPORTS, tmp_path / "output")
    assert ir_digest() == before


def test_inspect_returns_original_suggestions_and_reasons(tmp_path: Path):
    output = tmp_path / "output"
    analyze_reports(FIXTURE_REPORTS, output)
    matches = inspect_output(output, "specific-tv")

    assert matches
    classification = next(
        item["data"] for item in matches if item["report"] == "file-classification.json"
    )
    assert classification["original"]["brand"] == "SAMSUNG"
    assert classification["confidence"] > 0
    assert classification["reasons"]


def test_real_inventory_format_preserves_commands_protocols_and_addresses():
    records, consumed = load_inventory(REAL_FORMAT_FIXTURE)
    converted = next(record for record in records if record.original_brand == "2wire")

    assert consumed == ["inventory.json"]
    assert converted.source_path.endswith("32_159.ir")
    assert [command.original_name for command in converted.commands] == [
        "POWER",
        "BACK",
        "UP",
        "VOL-",
        "VOL+",
    ]
    assert {command.protocol for command in converted.commands} == {"NECext"}
    assert {command.address for command in converted.commands} == {"20 9F 00 00"}


def test_real_numeric_conversion_name_is_not_a_model():
    records, _ = load_inventory(REAL_FORMAT_FIXTURE)
    converted = next(record for record in records if record.original_brand == "2wire")
    result = extract_model(converted)

    assert result["candidate"] is None
    assert result["requires_review"]


def test_real_universal_pattern_is_not_specific_device():
    records, _ = load_inventory(REAL_FORMAT_FIXTURE)
    universal = next(record for record in records if "Universal" in record.source_path)
    model = extract_model(universal)
    category = suggest_category(universal.original_category, universal.source_path)
    brand = suggest_brand(universal.original_brand, universal.source_path)
    result = classify(universal, model, category, brand)

    assert result["classification"] in {"universal_remote", "brute_force"}
    assert result["evidence"]["sequential_group_count"] >= 1


def classified(
    path: str,
    category: str,
    brand: str,
    model: str,
    names: tuple[str, ...],
    *,
    with_protocol: bool = True,
) -> tuple[dict, dict]:
    commands = tuple(
        CommandRecord(name, "NEC" if with_protocol else None, "0x01" if with_protocol else None)
        for name in names
    )
    item = record(
        path,
        category=category,
        brand=brand,
        model=model,
        category_confidence=0.85,
        brand_confidence=0.7,
        model_confidence=0.75,
        commands=commands,
    )
    model_result = extract_model(item)
    result = classify(
        item,
        model_result,
        suggest_category(category, path),
        suggest_brand(brand, path),
    )
    return result, model_result


def test_projector_benq_commands_are_contextual_not_mixed():
    result, _ = classified(
        "Projectors/BenQ/TK800M.ir",
        "Projectors",
        "BenQ",
        "TK800M",
        ("Power", "Eco", "Lamp", "Focus", "Zoom", "Input"),
    )
    assert result["classification"] != "mixed_collection"
    assert result["evidence"]["incompatible_semantic_groups"] == []


def test_projector_sony_commands_are_contextual_not_mixed():
    result, _ = classified(
        "Projectors/Sony/RM_PJ24.ir",
        "Projectors",
        "Sony",
        "RM_PJ24",
        ("Power", "Focus", "Zoom", "Shift", "Position"),
    )
    assert result["classification"] != "mixed_collection"
    assert result["evidence"]["incompatible_semantic_groups"] == []


def test_tv_temperature_command_is_strong_mixed_evidence():
    result, _ = classified(
        "TVs/Samsung/AU7700.ir",
        "TVs",
        "Samsung",
        "AU7700",
        ("Power", "Volume+", "Temperature Up"),
    )
    assert result["classification"] == "mixed_collection"
    assert any("Temperature Up" in reason for reason in result["reasons"])


def test_filename_universal_marker_has_precedence():
    result, _ = classified(
        "TVs/Generic/Generic_Universal_Remote.ir",
        "TVs",
        "Generic",
        "Generic_Universal_Remote",
        ("Power", "Volume+"),
    )
    assert result["classification"] == "universal_remote"


def test_folder_universal_marker_has_precedence():
    result, _ = classified(
        "Universal_TV_Remotes/Brand/ModelX.ir",
        "TVs",
        "Brand",
        "ModelX",
        ("Power", "Volume+"),
    )
    assert result["classification"] == "universal_remote"


def test_numbered_power_collection_remains_brute_force():
    commands = tuple(CommandRecord(f"Power{i}", "NEC", f"0x{i:02X}") for i in range(1, 9))
    item = record(
        "TVs/Brand/Power_Codes.ir",
        category="TVs",
        brand="Brand",
        commands=commands,
        signal_count=128,
    )
    result = classify(item, extract_model(item))
    assert result["classification"] == "brute_force"


def test_zero_protocols_are_reported_as_insufficient_not_coherent():
    result, _ = classified(
        "TVs/Samsung/AU7700.ir",
        "TVs",
        "Samsung",
        "AU7700",
        ("Power", "Volume+"),
        with_protocol=False,
    )
    all_reasons = " ".join(result["reasons"]).casefold()
    assert result["evidence"]["protocol_count"] == 0
    assert "coerente" not in all_reasons
    assert "insuficientes" in all_reasons


def test_unknown_prefix_keeps_plausible_model_at_moderate_confidence():
    result = extract_model(record("Fans/Unknown/Unknown_RC-ZVR02.ir"))
    assert result["candidate"] == "RC-ZVR02"
    assert result["cleaned_candidate"] == "RC-ZVR02"
    assert 0.4 <= result["confidence"] < 0.8
    assert result["requires_review"]


def test_unknown_numeric_suffix_is_not_a_model():
    result = extract_model(record("Fans/Unknown/Unknown_9067.ir"))
    assert result["candidate"] is None
    assert result["cleaned_candidate"] is None
    assert result["requires_review"]
