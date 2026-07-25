"""Leitura tolerante dos relatórios e geração das propostas auditáveis."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .brands import suggest_brand
from .categories import suggest_category
from .classifier import CLASSES, classify
from .commands import suggest_command
from .models import CommandRecord, InventoryRecord
from .models_extractor import extract_model

KNOWN_REPORTS = (
    "inventory.json",
    "inventory.csv",
    "categories.json",
    "brands.json",
    "commands.json",
    "protocols.json",
    "duplicates.json",
    "raw-analysis.json",
    "parse-errors.json",
)


def _first(data: dict[str, Any], keys: Iterable[str], default=None):
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                return parsed if isinstance(parsed, list) else [value]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in value.split("|") if item.strip()]
    return [value]


def _commands(data: dict[str, Any]) -> tuple[CommandRecord, ...]:
    values = _first(data, ("commands", "signals", "buttons", "entries"), [])
    result = []
    for value in _as_list(values):
        if isinstance(value, str):
            result.append(CommandRecord(value))
        elif isinstance(value, dict):
            name = _first(value, ("original_name", "name", "command", "button"))
            if name is not None:
                result.append(
                    CommandRecord(
                        str(name),
                        str(_first(value, ("protocol", "type"), "")) or None,
                        str(_first(value, ("address", "addr"), "")) or None,
                    )
                )
    return tuple(result)


def _looks_like_file_record(data: dict[str, Any]) -> bool:
    return any(key in data for key in ("path", "file", "file_path", "source_path"))


def _record(data: dict[str, Any], source_report: str, index: int) -> InventoryRecord:
    path = str(
        _first(data, ("source_path", "file_path", "path", "file"), f"{source_report}#{index}")
    )
    record_id = str(
        _first(
            data,
            ("id", "file_id", "record_id"),
            hashlib.sha256(path.encode("utf-8")).hexdigest()[:16],
        )
    )
    commands = _commands(data)
    signal_count = int(
        _first(data, ("signal_count", "command_count", "commands_count"), len(commands)) or 0
    )
    return InventoryRecord(
        record_id=record_id,
        source_path=path,
        original_category=_first(data, ("category", "device_category", "type")),
        original_brand=_first(data, ("brand", "manufacturer_brand")),
        original_model=_first(data, ("model", "device_model")),
        comments=tuple(str(item) for item in _as_list(_first(data, ("comments", "notes")))),
        commands=commands,
        signal_count=signal_count,
        duplicate_count=int(
            _first(data, ("duplicate_count", "duplicates_count", "identical_signals"), 0) or 0
        ),
        parse_errors=tuple(
            str(item) for item in _as_list(_first(data, ("parse_errors", "errors")))
        ),
        source_report=source_report,
        original_data=data,
    )


def _find_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        direct = [
            item for item in value if isinstance(item, dict) and _looks_like_file_record(item)
        ]
        if direct:
            return direct
        result = []
        for item in value:
            result.extend(_find_records(item))
        return result
    if isinstance(value, dict):
        if _looks_like_file_record(value):
            return [value]
        for key in ("files", "records", "items", "inventory", "results"):
            if key in value:
                found = _find_records(value[key])
                if found:
                    return found
    return []


def load_inventory(report_dir: Path) -> tuple[list[InventoryRecord], list[str]]:
    records: dict[str, InventoryRecord] = {}
    consumed = []

    for name in KNOWN_REPORTS:
        path = report_dir / name
        if not path.exists():
            continue
        consumed.append(name)
        if path.suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                raw_records = list(csv.DictReader(stream))
        else:
            with path.open(encoding="utf-8") as stream:
                raw_records = _find_records(json.load(stream))
        for index, raw in enumerate(raw_records):
            candidate = _record(raw, name, index)
            records.setdefault(candidate.source_path, candidate)

    ordered = sorted(records.values(), key=lambda item: (item.source_path, item.record_id))
    return ordered, sorted(consumed)


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _dump_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fields})


def _unique_proposals(rows: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    unique = {}
    for row in rows:
        key = tuple(json.dumps(row.get(field), sort_keys=True) for field in key_fields)
        if key not in unique:
            unique[key] = row
        elif "examples" in row:
            examples = sorted(set(unique[key]["examples"]) | set(row["examples"]))
            unique[key]["examples"] = examples
    return sorted(
        unique.values(), key=lambda row: tuple(str(row.get(field)) for field in key_fields)
    )


def analyze_reports(report_dir: Path, output_dir: Path) -> dict[str, Any]:
    records, consumed = load_inventory(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    category_rows = []
    brand_rows = []
    model_rows = []
    command_rows = []
    classification_rows = []
    conflicts = []
    review_queue = []

    for record in records:
        category = suggest_category(record.original_category, record.source_path)
        brand = suggest_brand(record.original_brand, record.source_path)
        model = extract_model(record)
        classification = classify(record, model)
        classification["suggested_device_type"] = category["normalized_value"]
        classification["device_type_confidence"] = category["confidence"]

        category_rows.append(category)
        brand_rows.append(brand)
        model_rows.append(model)
        classification_rows.append(classification)

        command_suggestions = [
            suggest_command(command.original_name, record.source_path)
            for command in record.commands
        ]
        command_rows.extend(command_suggestions)

        record_conflicts = []
        if classification["conflicts"]:
            record_conflicts.append(
                {"field": "classification", "candidates": classification["conflicts"]}
            )
        if category["normalized_value"] is None:
            record_conflicts.append({"field": "category", "candidates": []})
        if model["ambiguity"] and model["alternatives"]:
            record_conflicts.append(
                {
                    "field": "model",
                    "candidates": [model["candidate"], *model["alternatives"]],
                }
            )
        if record_conflicts:
            conflicts.append(
                {
                    "record_id": record.record_id,
                    "source_path": record.source_path,
                    "conflicts": record_conflicts,
                }
            )

        review_reasons = []
        if classification["requires_review"]:
            review_reasons.append("classificação abaixo do limiar automático ou conflitante")
        if category["confidence"] < 0.8:
            review_reasons.append("categoria ambígua ou ausente")
        if brand["requires_review"]:
            review_reasons.append("marca ambígua ou ausente")
        if model["requires_review"]:
            review_reasons.append("modelo ambíguo ou ausente")
        if any(item["requires_review"] for item in command_suggestions):
            review_reasons.append("um ou mais comandos exigem revisão")
        if review_reasons:
            review_queue.append(
                {
                    "record_id": record.record_id,
                    "source_path": record.source_path,
                    "priority": "high" if len(review_reasons) >= 3 else "normal",
                    "reasons": sorted(set(review_reasons)),
                    "original": classification["original"],
                }
            )

    category_map = _unique_proposals(
        category_rows, ("source_value", "normalized_value", "rule_type")
    )
    brand_map = _unique_proposals(brand_rows, ("original", "suggested_brand_id"))
    aliases_by_id: dict[str, list[str]] = {}
    for row in brand_map:
        brand_id = row["suggested_brand_id"]
        if brand_id and row["original"]:
            aliases_by_id.setdefault(brand_id, []).append(row["original"])
    for row in brand_map:
        brand_id = row["suggested_brand_id"]
        row["possible_aliases"] = sorted(set(aliases_by_id.get(brand_id, [])))
    command_map = _unique_proposals(command_rows, ("original", "canonical_name"))

    classification_rows.sort(key=lambda row: (row["source_path"], row["record_id"]))
    model_rows.sort(key=lambda row: (row["source_path"], row["record_id"]))
    conflicts.sort(key=lambda row: (row["source_path"], row["record_id"]))
    review_queue.sort(key=lambda row: (row["priority"], row["source_path"], row["record_id"]))

    _dump_json(output_dir / "category-map.proposed.json", category_map)
    _dump_json(output_dir / "brand-map.proposed.json", brand_map)
    _dump_json(output_dir / "command-aliases.proposed.json", command_map)
    _dump_json(output_dir / "model-candidates.json", model_rows)
    _dump_json(output_dir / "file-classification.json", classification_rows)
    _dump_json(output_dir / "conflicts.json", conflicts)
    _dump_json(output_dir / "review-queue.json", review_queue)

    _dump_csv(
        csv_dir / "file-classification.csv",
        classification_rows,
        [
            "record_id",
            "source_path",
            "classification",
            "suggested_device_type",
            "device_type_confidence",
            "confidence",
            "reasons",
            "conflicts",
            "requires_review",
        ],
    )
    _dump_csv(
        csv_dir / "brand-map.csv",
        brand_map,
        [
            "original",
            "suggested_brand_id",
            "display_name",
            "manufacturer",
            "confidence",
            "rule",
            "reasons",
            "requires_review",
        ],
    )
    _dump_csv(
        csv_dir / "model-candidates.csv",
        model_rows,
        [
            "record_id",
            "source_path",
            "original_text",
            "candidate",
            "confidence",
            "extraction_source",
            "ambiguity",
            "alternatives",
            "requires_review",
        ],
    )
    _dump_csv(
        csv_dir / "command-aliases.csv",
        command_map,
        [
            "original",
            "canonical_name",
            "confidence",
            "rule",
            "reasons",
            "ambiguity",
            "requires_review",
        ],
    )
    _dump_csv(
        csv_dir / "review-queue.csv",
        review_queue,
        ["record_id", "source_path", "priority", "reasons", "original"],
    )

    class_counts = Counter(row["classification"] for row in classification_rows)
    summary = {
        "input_directory": report_dir.as_posix(),
        "reports_consumed": consumed,
        "records": len(records),
        "classification_counts": {name: class_counts.get(name, 0) for name in CLASSES},
        "category_suggestions": sum(row["normalized_value"] is not None for row in category_map),
        "brands_suggested": sum(row["suggested_brand_id"] is not None for row in brand_map),
        "models_identified": sum(row["candidate"] is not None for row in model_rows),
        "commands_mapped": sum(row["canonical_name"] is not None for row in command_map),
        "conflicts": len(conflicts),
        "review_queue": len(review_queue),
        "warning": None
        if consumed
        else "Nenhum relatório conhecido foi encontrado; saídas vazias foram geradas.",
    }
    lines = [
        "# OpenIR normalization summary",
        "",
        f"- Diretório de entrada: `{summary['input_directory']}`",
        f"- Relatórios consumidos: {', '.join(consumed) if consumed else 'nenhum'}",
        f"- Arquivos classificados: {summary['records']}",
        f"- Categorias sugeridas: {summary['category_suggestions']}",
        f"- Marcas sugeridas: {summary['brands_suggested']}",
        f"- Modelos identificados: {summary['models_identified']}",
        f"- Comandos mapeados: {summary['commands_mapped']}",
        f"- Conflitos: {summary['conflicts']}",
        f"- Fila de revisão: {summary['review_queue']}",
        "",
        "## Classificações",
        "",
        *[f"- `{name}`: {summary['classification_counts'][name]}" for name in CLASSES],
    ]
    if summary["warning"]:
        lines.extend(["", "## Advertência", "", summary["warning"]])
    (output_dir / "normalization-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def inspect_output(output_dir: Path, query: str) -> list[dict]:
    matches = []
    query_key = query.casefold()
    for name in (
        "file-classification.json",
        "model-candidates.json",
        "conflicts.json",
        "review-queue.json",
    ):
        path = output_dir / name
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            searchable = f"{row.get('record_id', '')} {row.get('source_path', '')}".casefold()
            if query_key in searchable:
                matches.append({"report": name, "data": row})
    return sorted(
        matches,
        key=lambda item: (
            str(item["data"].get("source_path", "")),
            item["report"],
        ),
    )
