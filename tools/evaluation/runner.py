"""Gera benchmark silver, métricas e auditorias independentes."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from .reference_rules import (
    REFERENCE_CLASSES,
    derive_reference,
    extensive_attempt_sequences,
    rule_counts,
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dump_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )


def _metrics(rows: list[dict], total_inventory: int) -> dict:
    total = len(rows)
    matched = sum(row["matched"] for row in rows)
    expected_counts = Counter(row["expected_classification"] for row in rows)
    predicted_counts = Counter(row["predicted_classification"] for row in rows)
    matrix = {
        expected: {
            predicted: sum(
                row["expected_classification"] == expected
                and row["predicted_classification"] == predicted
                for row in rows
            )
            for predicted in sorted(set(predicted_counts) | set(REFERENCE_CLASSES))
        }
        for expected in sorted(expected_counts)
    }
    per_class = {}
    for name in sorted(expected_counts):
        true_positive = matrix[name].get(name, 0)
        precision = true_positive / predicted_counts[name] if predicted_counts[name] else None
        recall = true_positive / expected_counts[name]
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and precision + recall
            else None
        )
        sufficient = expected_counts[name] >= 20
        per_class[name] = {
            "examples": expected_counts[name],
            "sample_status": "sufficient" if sufficient else "insufficient",
            "precision": round(precision, 6) if sufficient and precision is not None else None,
            "recall": round(recall, 6) if sufficient else None,
            "f1": round(f1, 6) if sufficient and f1 is not None else None,
        }
    errors = [row for row in rows if not row["matched"]]
    return {
        "benchmark_size": total,
        "inventory_size": total_inventory,
        "coverage": round(total / total_inventory, 6) if total_inventory else 0,
        "accuracy": round(matched / total, 6) if total else None,
        "matched": matched,
        "errors": len(errors),
        "errors_confidence_gte_080": sum(row["predicted_confidence"] >= 0.8 for row in errors),
        "errors_confidence_gte_095": sum(row["predicted_confidence"] >= 0.95 for row in errors),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "reference_rule_counts": rule_counts(rows),
    }


def _audit_invariants(
    records: list[dict],
    predictions: dict[str, dict],
    models: dict[str, dict],
    parse_errors: set[str],
) -> dict:
    violations = []

    def add(path: str, invariant: str, details: dict) -> None:
        violations.append({"path": path, "invariant": invariant, "details": details})

    for record in sorted(records, key=lambda item: item["relative_path"]):
        path = record["relative_path"]
        prediction = predictions.get(path)
        if not prediction:
            add(path, "missing_prediction", {})
            continue
        predicted = prediction["classification"]
        model = models.get(path, {})
        candidate = model.get("candidate")
        original = prediction.get("original", {})
        evidence = prediction.get("evidence", {})
        conflicts = prediction.get("conflicts", [])
        if path.casefold().startswith("universal_tv_remotes/") and predicted != "universal_remote":
            add(path, "universal_directory_not_universal", {"predicted": predicted})
        if path in parse_errors and predicted != "malformed":
            add(path, "parse_error_not_malformed", {"predicted": predicted})
        extensive = extensive_attempt_sequences(record.get("command_names", []))
        if extensive and predicted != "brute_force":
            add(
                path,
                "extensive_power_or_intent_sequence_not_brute_force",
                {"predicted": predicted, "sequences": extensive},
            )
        if predicted == "specific_device" and not candidate:
            add(path, "specific_device_without_model", {})
        if predicted == "specific_device" and str(original.get("brand", "")).casefold() in {
            "",
            "unknown",
            "generic",
            "misc",
        }:
            add(path, "specific_device_with_unknown_brand", {"brand": original.get("brand")})
        if predicted == "specific_device" and str(original.get("category", "")).casefold() in {
            "",
            "unknown",
        }:
            add(
                path,
                "specific_device_with_unknown_category",
                {"category": original.get("category")},
            )
        if predicted == "universal_remote" and candidate and not conflicts:
            add(path, "universal_with_specific_model_without_conflict", {"model": candidate})
        reasons = " ".join(prediction.get("reasons", [])).casefold()
        if (
            evidence.get("protocol_count", 0) == 0
            and evidence.get("address_count", 0) == 0
            and ("dados técnicos observados" in reasons or "tecnicamente coerente" in reasons)
        ):
            add(path, "technical_claim_without_protocol_or_address", {})
        brand = str(original.get("brand") or "")
        if candidate and candidate.casefold() == brand.casefold():
            add(path, "model_equals_brand", {"model": candidate, "brand": brand})
        if candidate and any(
            marker in candidate.casefold()
            for marker in ("unknown", "generic", "universal", "remote")
        ):
            justification = " ".join(model.get("reasons", [])).casefold()
            if not any(word in justification for word in ("removido", "preservado", "plausível")):
                add(
                    path,
                    "generic_marker_in_model_without_justification",
                    {"model": candidate},
                )
    counts = Counter(item["invariant"] for item in violations)
    return {
        "inventory_size": len(records),
        "violation_count": len(violations),
        "counts": dict(sorted(counts.items())),
        "violations": violations,
    }


def _benchmark_markdown(metrics: dict) -> str:
    lines = [
        "# Silver benchmark da normalização OpenIR",
        "",
        f"- Casos: {metrics['benchmark_size']}",
        f"- Cobertura: {metrics['coverage']:.2%}",
        f"- Acurácia: {metrics['accuracy']:.2%}",
        f"- Erros com confiança ≥ 0,80: {metrics['errors_confidence_gte_080']}",
        f"- Erros com confiança ≥ 0,95: {metrics['errors_confidence_gte_095']}",
        "",
        "## Métricas por classe",
        "",
        "| Classe | Exemplos | Status | Precisão | Recall | F1 |",
        "|---|---:|---|---:|---:|---:|",
    ]
    for name, item in metrics["per_class"].items():
        render = lambda value: "—" if value is None else f"{value:.3f}"  # noqa: E731
        lines.append(
            f"| `{name}` | {item['examples']} | {item['sample_status']} | "
            f"{render(item['precision'])} | {render(item['recall'])} | {render(item['f1'])} |"
        )
    columns = sorted(
        {predicted for row in metrics["confusion_matrix"].values() for predicted in row}
    )
    lines.extend(
        [
            "",
            "## Matriz de confusão",
            "",
            "| Esperado \\ Previsto | " + " | ".join(f"`{name}`" for name in columns) + " |",
            "|---|" + "---:|" * len(columns),
        ]
    )
    for expected, values in metrics["confusion_matrix"].items():
        lines.append(
            f"| `{expected}` | " + " | ".join(str(values.get(name, 0)) for name in columns) + " |"
        )
    lines.extend(["", "## Casos por regra", ""])
    lines.extend(f"- `{name}`: {count}" for name, count in metrics["reference_rule_counts"].items())
    lines.extend(
        [
            "",
            "As referências são derivadas antes da associação com a classificação prevista.",
            "Classes com menos de 20 exemplos são marcadas como amostra insuficiente.",
        ]
    )
    return "\n".join(lines) + "\n"


def _errors_markdown(errors: list[dict]) -> str:
    lines = ["# Erros do silver benchmark", "", f"- Total: {len(errors)}", ""]
    for row in errors:
        lines.append(
            f"- `{row['path']}`: esperado `{row['expected_classification']}`, previsto "
            f"`{row['predicted_classification']}` ({row['predicted_confidence']:.2f}); "
            f"regra `{row['reference_rule_id']}`."
        )
    return "\n".join(lines) + "\n"


def _audit_markdown(audit: dict) -> str:
    lines = [
        "# Auditoria de invariantes da normalização OpenIR",
        "",
        f"- Registros auditados: {audit['inventory_size']}",
        f"- Violações: {audit['violation_count']}",
        "",
        "## Contagem por invariante",
        "",
    ]
    lines.extend(f"- `{name}`: {count}" for name, count in audit["counts"].items())
    lines.extend(["", "## Violações", ""])
    lines.extend(f"- `{item['path']}` — `{item['invariant']}`" for item in audit["violations"])
    return "\n".join(lines) + "\n"


def generate(inventory: Path, normalization: Path, output: Path) -> dict:
    inventory_data = _load(inventory / "inventory.json")
    records = inventory_data["files"]
    parse_error_rows = _load(inventory / "parse-errors.json")
    parse_errors = {item["path"] for item in parse_error_rows if item.get("severity") == "error"}
    predictions = {
        item["source_path"]: item for item in _load(normalization / "file-classification.json")
    }
    models = {item["source_path"]: item for item in _load(normalization / "model-candidates.json")}

    references = []
    for record in sorted(records, key=lambda item: item["relative_path"]):
        reference = derive_reference(record, parse_errors)
        if not reference:
            continue
        path = record["relative_path"]
        prediction = predictions.get(path)
        if not prediction:
            continue
        expected = reference["expected_classification"]
        predicted = prediction["classification"]
        references.append(
            {
                "path": path,
                "expected_classification": expected,
                "predicted_classification": predicted,
                "predicted_confidence": prediction["confidence"],
                "reference_rule_id": reference["reference_rule_id"],
                "reference_evidence": reference["reference_evidence"],
                "matched": expected == predicted,
                "review_reason": (
                    "" if expected == predicted else "predição diverge da regra silver"
                ),
            }
        )
    metrics = _metrics(references, len(records))
    errors = [row for row in references if not row["matched"]]
    audit = _audit_invariants(records, predictions, models, parse_errors)
    output.mkdir(parents=True, exist_ok=True)
    fields = [
        "path",
        "expected_classification",
        "predicted_classification",
        "predicted_confidence",
        "reference_rule_id",
        "reference_evidence",
        "matched",
        "review_reason",
    ]
    _dump_json(output / "reference-benchmark.json", {"metrics": metrics, "records": references})
    _dump_csv(output / "reference-benchmark.csv", references, fields)
    (output / "reference-benchmark.md").write_text(_benchmark_markdown(metrics), encoding="utf-8")
    _dump_csv(output / "reference-errors.csv", errors, fields)
    (output / "reference-errors.md").write_text(_errors_markdown(errors), encoding="utf-8")
    _dump_json(output / "invariant-audit.json", audit)
    (output / "invariant-audit.md").write_text(_audit_markdown(audit), encoding="utf-8")

    high_errors = sorted(errors, key=lambda row: (-row["predicted_confidence"], row["path"]))[:10]
    selected = {
        row["path"]: {**row, "selection_reason": "high_confidence_error"} for row in high_errors
    }
    boundaries = sorted(
        references,
        key=lambda row: (abs(row["predicted_confidence"] - 0.72), row["path"]),
    )
    for row in boundaries:
        if row["path"] not in selected:
            selected[row["path"]] = {**row, "selection_reason": "decision_boundary"}
        if sum(item["selection_reason"] == "decision_boundary" for item in selected.values()) >= 10:
            break
    for violation in audit["violations"]:
        if violation["path"] not in selected:
            prediction = predictions.get(violation["path"], {})
            selected[violation["path"]] = {
                "path": violation["path"],
                "expected_classification": "",
                "predicted_classification": prediction.get("classification", ""),
                "predicted_confidence": prediction.get("confidence", ""),
                "reference_rule_id": "",
                "reference_evidence": violation["details"],
                "matched": "",
                "review_reason": violation["invariant"],
                "selection_reason": "invariant_violation",
            }
        if (
            sum(item["selection_reason"] == "invariant_violation" for item in selected.values())
            >= 10
        ):
            break
    review_rows = sorted(selected.values(), key=lambda row: (row["selection_reason"], row["path"]))
    _dump_csv(
        output / "minimal-review-sample.csv",
        review_rows,
        fields + ["selection_reason"],
    )
    return {
        **metrics,
        "invariant_violations": audit["violation_count"],
        "minimal_review_sample": len(review_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    benchmark = subparsers.add_parser("reference-benchmark")
    benchmark.add_argument("--inventory", type=Path, required=True)
    benchmark.add_argument("--normalization", type=Path, required=True)
    benchmark.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = generate(arguments.inventory, arguments.normalization, arguments.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0
