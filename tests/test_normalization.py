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
