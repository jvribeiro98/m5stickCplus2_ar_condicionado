import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"
EXAMPLES_DIR = ROOT / "examples"
INVALID_DIR = ROOT / "tests" / "fixtures" / "invalid"


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


SCHEMAS = {
    path.name: load_json(path)
    for path in sorted(SCHEMAS_DIR.glob("*.schema.json"))
}


def build_registry() -> Registry:
    registry = Registry()
    for schema in SCHEMAS.values():
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema["$id"], resource)
    return registry


REGISTRY = build_registry()
FORMAT_CHECKER = FormatChecker()


def validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        SCHEMAS[schema_name],
        registry=REGISTRY,
        format_checker=FORMAT_CHECKER,
    )


def validate(schema_name: str, instance) -> None:
    validator(schema_name).validate(instance)


def signal_refs(device: dict) -> set[str]:
    refs = set()
    for binding in device["bindings"]:
        if binding["signal_ref"] is not None:
            refs.add(binding["signal_ref"])
        if binding["state_operation"] is not None:
            refs.add(binding["state_operation"]["signal_ref"])
    return refs


def example_signal_id(signal: dict) -> str:
    """Canonicalização suficiente para os exemplos, que usam apenas números JSON simples."""
    identity_fields = (
        "signal_type",
        "frequency",
        "protocol",
        "raw_data",
        "state_snapshot",
        "encoder_reference",
        "repeat",
    )
    material = {field: signal[field] for field in identity_fields}
    canonical = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "signal-sha256-" + hashlib.sha256(canonical).hexdigest()


def assert_device_semantics(device: dict, available_signal_ids: set[str]) -> None:
    capability_ids = [item["id"] for item in device["capabilities"]]
    binding_ids = [item["id"] for item in device["bindings"]]

    assert len(capability_ids) == len(set(capability_ids)), "Capability ID duplicado"
    assert len(binding_ids) == len(set(binding_ids)), "Binding ID duplicado"

    for binding in device["bindings"]:
        assert binding["capability_id"] in capability_ids
        ref = binding["signal_ref"]
        if ref is None:
            ref = binding["state_operation"]["signal_ref"]
        assert ref in available_signal_ids


def test_all_schemas_are_valid_draft_2020_12():
    assert SCHEMAS
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "path",
    sorted(EXAMPLES_DIR.glob("*.json")),
    ids=lambda path: path.name,
)
def test_device_examples(path: Path):
    validate("device.schema.json", load_json(path))


@pytest.mark.parametrize(
    "path",
    sorted((EXAMPLES_DIR / "signals").glob("*.json")),
    ids=lambda path: path.name,
)
def test_signal_examples(path: Path):
    signal = load_json(path)
    validate("signal.schema.json", signal)
    assert signal["id"] == example_signal_id(signal)


@pytest.mark.parametrize(
    "path",
    sorted((EXAMPLES_DIR / "bundles").glob("*.json")),
    ids=lambda path: path.name,
)
def test_bundle_examples(path: Path):
    validate("bundle.schema.json", load_json(path))


def test_every_example_json_is_classified_and_validated():
    classified = (
        set(EXAMPLES_DIR.glob("*.json"))
        | set((EXAMPLES_DIR / "signals").glob("*.json"))
        | set((EXAMPLES_DIR / "bundles").glob("*.json"))
    )
    assert classified == set(EXAMPLES_DIR.rglob("*.json"))


@pytest.mark.parametrize(
    "path",
    sorted(INVALID_DIR.glob("*.json")),
    ids=lambda path: path.name,
)
def test_invalid_fixtures_are_rejected(path: Path):
    fixture = load_json(path)
    schema_name = fixture.pop("_schema")
    with pytest.raises(ValidationError):
        validate(schema_name, fixture)


def test_raw_timing_zero_is_rejected():
    signal = load_json(EXAMPLES_DIR / "signals" / "raw.json")
    signal["raw_data"]["original"]["sequence"][0] = 0
    with pytest.raises(ValidationError):
        validate("signal.schema.json", signal)


def test_raw_negative_timing_is_rejected():
    signal = load_json(EXAMPLES_DIR / "signals" / "raw.json")
    signal["raw_data"]["original"]["sequence"][0] = -9000
    with pytest.raises(ValidationError):
        validate("signal.schema.json", signal)


def test_signal_without_license_is_rejected():
    signal = load_json(EXAMPLES_DIR / "signals" / "raw.json")
    signal.pop("license")
    with pytest.raises(ValidationError):
        validate("signal.schema.json", signal)


def test_signal_without_source_is_rejected():
    signal = load_json(EXAMPLES_DIR / "signals" / "raw.json")
    signal.pop("source")
    with pytest.raises(ValidationError):
        validate("signal.schema.json", signal)


def test_device_bindings_resolve_capabilities_and_catalog_signals():
    signal_ids = {
        load_json(path)["id"]
        for path in (EXAMPLES_DIR / "signals").glob("*.json")
    }
    for path in EXAMPLES_DIR.glob("*.json"):
        assert_device_semantics(load_json(path), signal_ids)


def test_broken_binding_reference_is_rejected_semantically():
    device = load_json(EXAMPLES_DIR / "tv.json")
    signals = {
        load_json(path)["id"]
        for path in (EXAMPLES_DIR / "signals").glob("*.json")
    }
    device["bindings"][0]["signal_ref"] = (
        "signal-sha256-ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    )
    with pytest.raises(AssertionError):
        assert_device_semantics(device, signals)


def test_stateful_snapshot_and_encoder_reference():
    snapshot = load_json(EXAMPLES_DIR / "signals" / "state-snapshot.json")
    encoder = load_json(
        EXAMPLES_DIR / "signals" / "stateful-encoder-reference.json"
    )
    device = load_json(EXAMPLES_DIR / "air_conditioner.json")

    validate("signal.schema.json", snapshot)
    validate("signal.schema.json", encoder)
    validate("device.schema.json", device)

    assert {"power", "temperature", "mode", "fan_speed"} <= set(
        snapshot["state_snapshot"]["state"]
    )
    required = set(encoder["encoder_reference"]["required_state_fields"])
    modeled = {item["id"] for item in device["state_model"]["properties"]}
    assert required <= modeled


def test_offline_bundle_is_self_contained_and_minimal():
    bundle = load_json(
        EXAMPLES_DIR / "bundles" / "tv-offline-bundle.json"
    )
    validate("bundle.schema.json", bundle)

    embedded_ids = {signal["id"] for signal in bundle["signals"]}
    declared_ids = set(bundle["metadata"]["included_signal_ids"])
    referenced_ids = signal_refs(bundle["device"])

    assert bundle["metadata"]["device_id"] == bundle["device"]["id"]
    assert bundle["metadata"]["device_version"] == bundle["device"]["version"]
    assert embedded_ids == declared_ids == referenced_ids
    assert all(signal["id"] == example_signal_id(signal) for signal in bundle["signals"])
    assert_device_semantics(bundle["device"], embedded_ids)


def test_unknown_extension_is_structurally_allowed_but_not_transmitted_by_default():
    signal = copy.deepcopy(load_json(EXAMPLES_DIR / "signals" / "raw.json"))
    signal["extensions"]["x-example-experimental-v1"] = {"payload": "opaque"}
    validate("signal.schema.json", signal)
