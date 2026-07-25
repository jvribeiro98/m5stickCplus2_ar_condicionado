"""Amostragem determinística do comportamento v1, sem alterar heurísticas."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _metrics(record: dict) -> dict:
    signals = record.get("signals", [])
    names = record.get("command_names", [])
    protocols = sorted(
        {str(signal.get("protocol")) for signal in signals if signal.get("protocol") is not None}
        | {str(item) for item in record.get("protocols", [])}
    )
    addresses = sorted(
        {
            str(signal.get("address_original"))
            for signal in signals
            if signal.get("address_original") is not None
        }
    )
    normalized_bases = [
        re.sub(r"[\s_-]?\d+$", "", name.strip(), flags=re.IGNORECASE).casefold() for name in names
    ]
    counts = Counter(normalized_bases)
    repeated = sum(value for value in counts.values() if value >= 2)
    sequential = sum(1 for name in names if re.search(r"(?:^|[\s_-])\d+$", name.strip()))
    return {
        "protocols": protocols,
        "addresses": addresses,
        "repeated_name_count": repeated,
        "sequential_name_count": sequential,
    }


def _problem_list(current: dict, record: dict, metrics: dict) -> list[str]:
    problems = []
    model = current.get("evidence", {}).get("model_candidate")
    inference = record.get("inference", {})
    inferred_model = inference.get("model", {})
    if inferred_model.get("confidence", 1) < 0.6 and model:
        problems.append("modelo de baixa confiança foi tratado como evidência estrutural")
    if current.get("evidence", {}).get("protocol_count", 0) == 0 and metrics["protocols"]:
        problems.append("protocolos reais não chegaram ao classificador")
    if not current.get("original", {}).get("command_names") and record.get("command_names"):
        problems.append("nomes de comandos reais não chegaram ao classificador")
    if metrics["sequential_name_count"] >= 3:
        problems.append("sequência numerada pode indicar codeset ou bruteforce")
    if metrics["repeated_name_count"] >= 8:
        problems.append("muitos nomes compartilham a mesma intenção")
    if current["classification"] == "specific_device" and not record.get("command_names"):
        problems.append("specific_device sem evidência interna de comandos")
    if current.get("conflicts"):
        problems.append("classificações concorrentes próximas")
    return sorted(set(problems))


def generate_v1_sample(
    inventory_path: Path,
    current_output: Path,
    analysis_output: Path,
) -> dict:
    inventory = load_json(inventory_path)
    raw_records = inventory["files"]
    by_path = {record["relative_path"]: record for record in raw_records}
    current = load_json(current_output / "file-classification.json")
    models = {
        item["record_id"]: item for item in load_json(current_output / "model-candidates.json")
    }

    enriched = []
    for item in current:
        source_path = item["source_path"]
        csv_match = re.fullmatch(r"inventory\.csv#(\d+)", source_path)
        if csv_match:
            index = int(csv_match.group(1))
            record = raw_records[index] if index < len(raw_records) else {}
        else:
            record = by_path.get(source_path, {})
        if not record:
            continue
        metrics = _metrics(record)
        inference = record.get("inference", {})
        enriched.append(
            {
                "record_id": item["record_id"],
                "path": record["relative_path"],
                "filename": record.get("filename", Path(record["relative_path"]).name),
                "original_category": inference.get("category", {}).get("value"),
                "original_brand": inference.get("brand", {}).get("value"),
                "suggested_model": models.get(item["record_id"], {}).get("candidate"),
                "signal_count": record.get("signal_count", 0),
                "command_names": record.get("command_names", []),
                "protocols": metrics["protocols"],
                "addresses": metrics["addresses"],
                "current_classification": item["classification"],
                "current_confidence": item["confidence"],
                "current_reasons": item["reasons"],
                "possible_problems": _problem_list(item, record, metrics),
                "repeated_name_count": metrics["repeated_name_count"],
                "sequential_name_count": metrics["sequential_name_count"],
                "selection_reasons": [],
            }
        )

    selected: dict[str, dict] = {}

    def add(rows: list[dict], reason: str, limit: int | None = 50) -> None:
        for row in rows if limit is None else rows[:limit]:
            selected.setdefault(row["record_id"], row)["selection_reasons"].append(reason)

    path_sorted = sorted(enriched, key=lambda row: row["path"])
    add(
        [row for row in path_sorted if row["current_classification"] == "specific_device"],
        "50 specific_device determinísticos",
    )
    add(
        [row for row in path_sorted if row["current_classification"] == "device_family"],
        "50 device_family determinísticos",
    )
    add(
        [row for row in path_sorted if row["current_classification"] == "unknown"],
        "todos os unknown",
        None,
    )
    add(
        sorted(enriched, key=lambda row: (-row["signal_count"], row["path"])),
        "50 maiores quantidades de comandos",
    )
    add(
        sorted(enriched, key=lambda row: (-row["repeated_name_count"], row["path"])),
        "50 maiores repetições de nomes",
    )
    add(
        sorted(enriched, key=lambda row: (-len(row["protocols"]), row["path"])),
        "50 maiores diversidades de protocolos",
    )
    add(
        sorted(enriched, key=lambda row: (-len(row["addresses"]), row["path"])),
        "50 maiores diversidades de endereços",
    )
    add(
        [
            row
            for row in sorted(
                enriched, key=lambda row: (-row["sequential_name_count"], row["path"])
            )
            if row["sequential_name_count"] > 0 or re.search(r"\d+(?:[_-]\d+)+", row["filename"])
        ],
        "50 nomes ou comandos com sequências numéricas",
    )
    add(
        [
            row
            for row in path_sorted
            if row["possible_problems"]
            or row["current_classification"] == "specific_device"
            and row["current_confidence"] < 0.8
        ],
        "50 registros com conflitos ou problemas",
    )

    rows = sorted(selected.values(), key=lambda row: row["path"])
    for row in rows:
        row["selection_reasons"] = sorted(set(row["selection_reasons"]))

    analysis_output.mkdir(parents=True, exist_ok=True)
    (analysis_output / "sample-review.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fields = [
        "record_id",
        "path",
        "filename",
        "original_category",
        "original_brand",
        "suggested_model",
        "signal_count",
        "command_names",
        "protocols",
        "addresses",
        "current_classification",
        "current_confidence",
        "current_reasons",
        "possible_problems",
        "selection_reasons",
    ]
    with (analysis_output / "sample-review.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: json.dumps(row[field], ensure_ascii=False, sort_keys=True)
                    if isinstance(row.get(field), (list, dict))
                    else row.get(field)
                    for field in fields
                }
            )
    selection_counts = Counter(reason for row in rows for reason in row["selection_reasons"])
    problem_counts = Counter(problem for row in rows for problem in row["possible_problems"])
    lines = [
        "# Revisão determinística da normalização v1",
        "",
        f"- Registros únicos na amostra: {len(rows)}",
        f"- Registros disponíveis para associação: {len(enriched)}",
        "",
        "## Cobertura dos critérios",
        "",
        *[f"- {reason}: {selection_counts[reason]}" for reason in sorted(selection_counts)],
        "",
        "## Problemas observados",
        "",
        *[f"- {problem}: {problem_counts[problem]}" for problem in sorted(problem_counts)],
        "",
        "Esta amostra foi gerada antes da alteração das heurísticas.",
    ]
    (analysis_output / "sample-review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "records": len(rows),
        "associated": len(enriched),
        "selection_counts": dict(sorted(selection_counts.items())),
        "problem_counts": dict(sorted(problem_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--current-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = generate_v1_sample(args.inventory, args.current_output, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
