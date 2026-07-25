import ast
import hashlib
import json
from pathlib import Path

from tools.evaluation.reference_rules import derive_reference
from tools.evaluation.runner import generate


def inventory_record(path: str, names: list[str] | None = None, **kwargs) -> dict:
    return {
        "relative_path": path,
        "filename": Path(path).name,
        "command_names": names or ["Power"],
        "signal_count": kwargs.pop("signal_count", len(names or ["Power"])),
        "issues": kwargs.pop("issues", []),
        **kwargs,
    }


def test_reference_universal_by_dedicated_folder():
    result = derive_reference(
        inventory_record("Universal_TV_Remotes/Sanyo/Sanyo_universal.ir"), set()
    )
    assert result["expected_classification"] == "universal_remote"
    assert result["reference_rule_id"] == "universal.dedicated_directory.v1"


def test_reference_bruteforce_by_extensive_power_sequence():
    names = [f"Power{i}" for i in range(1, 13)]
    result = derive_reference(inventory_record("TVs/Brand/Power_Codes.ir", names), set())
    assert result["expected_classification"] == "brute_force"


def test_reference_specific_by_brand_model_filename():
    result = derive_reference(inventory_record("TVs/Samsung/Samsung_AU7700.ir"), set())
    assert result["expected_classification"] == "specific_device"


def test_reference_family_without_model():
    result = derive_reference(inventory_record("TVs/Samsung/Samsung.ir"), set())
    assert result["expected_classification"] == "device_family"


def test_reference_malformed_by_parse_error():
    path = "TVs/Brand/Broken.ir"
    result = derive_reference(inventory_record(path), {path})
    assert result["expected_classification"] == "malformed"


def test_reference_rules_do_not_import_classifier_or_normalization_confidence():
    source = Path("tools/evaluation/reference_rules.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any("classifier" in name for name in imports)
    assert not any("normalization.confidence" in name for name in imports)


def test_ambiguous_record_does_not_enter_reference_benchmark():
    result = derive_reference(
        inventory_record("Miscellaneous/Unknown/remote.ir", ["Power", "Mode"]),
        set(),
    )
    assert result is None


def _digest(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def test_evaluation_outputs_are_deterministic(tmp_path: Path):
    reports = tmp_path / "reports"
    normalization = tmp_path / "normalization"
    reports.mkdir()
    normalization.mkdir()
    record = inventory_record("TVs/Samsung/Samsung_AU7700.ir")
    (reports / "inventory.json").write_text(json.dumps({"files": [record]}), encoding="utf-8")
    (reports / "parse-errors.json").write_text("[]", encoding="utf-8")
    prediction = {
        "source_path": record["relative_path"],
        "classification": "specific_device",
        "confidence": 0.9,
        "conflicts": [],
        "reasons": [],
        "original": {"brand": "Samsung", "category": "TVs"},
        "evidence": {"protocol_count": 1, "address_count": 1},
    }
    model = {
        "source_path": record["relative_path"],
        "candidate": "AU7700",
        "reasons": [],
    }
    (normalization / "file-classification.json").write_text(
        json.dumps([prediction]), encoding="utf-8"
    )
    (normalization / "model-candidates.json").write_text(json.dumps([model]), encoding="utf-8")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(reports, normalization, first)
    generate(reports, normalization, second)
    assert _digest(first) == _digest(second)
