"""Comparação determinística entre duas execuções da normalização."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

UNIVERSAL_PATTERN = re.compile(
    r"(?:universal(?:[_\s-]+remote)?|codeset|code[_\s-]+set|all[_\s-]+models|multi[_\s-]+brand)",
    re.IGNORECASE,
)


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _indexed(directory: Path, filename: str) -> dict[str, dict]:
    return {item["source_path"]: item for item in _load(directory / filename)}


def _examples(changes: list[tuple[str, str, str]], limit: int = 10) -> list[str]:
    if not changes:
        return ["- Nenhum caso."]
    return [
        f"- `{path}`: `{before}` → `{after}`" for path, before, after in sorted(changes)[:limit]
    ]


def generate_comparison(v2: Path, v3: Path, output: Path) -> dict:
    before = _indexed(v2, "file-classification.json")
    after = _indexed(v3, "file-classification.json")
    before_models = _indexed(v2, "model-candidates.json")
    after_models = _indexed(v3, "model-candidates.json")
    common = sorted(before.keys() & after.keys())
    class_before = Counter(before[path]["classification"] for path in common)
    class_after = Counter(after[path]["classification"] for path in common)

    def transitions(old: str | None, new: str | None) -> list[tuple[str, str, str]]:
        return [
            (path, before[path]["classification"], after[path]["classification"])
            for path in common
            if (old is None or before[path]["classification"] == old)
            and (new is None or after[path]["classification"] == new)
            and before[path]["classification"] != after[path]["classification"]
        ]

    mixed_corrected = transitions("mixed_collection", None)
    new_mixed = transitions(None, "mixed_collection")
    lost_universal = transitions("universal_remote", None)
    universal_corrected = [
        item for item in transitions(None, "universal_remote") if UNIVERSAL_PATTERN.search(item[0])
    ]
    unknown_models = []
    for path in common:
        old_candidate = before_models.get(path, {}).get("candidate")
        if isinstance(old_candidate, str) and old_candidate.casefold().startswith("unknown"):
            unknown_models.append(
                (
                    path,
                    old_candidate,
                    after_models.get(path, {}).get("candidate") or "sem candidato",
                )
            )

    classes = sorted(set(class_before) | set(class_after))
    lines = [
        "# Comparação da normalização v2 → v3",
        "",
        f"- Registros comparáveis: {len(common)}",
        f"- Falsos mistos corrigidos: {len(mixed_corrected)}",
        f"- Marcadores universais corrigidos: {len(universal_corrected)}",
        f"- Modelos `Unknown_*` limpos ou descartados: {len(unknown_models)}",
        f"- Novos casos mistos para auditoria: {len(new_mixed)}",
        f"- Casos universais perdidos para auditoria: {len(lost_universal)}",
        "",
        "## Distribuição por classe",
        "",
        "| Classe | v2 | v3 | Diferença |",
        "|---|---:|---:|---:|",
        *[
            f"| `{name}` | {class_before[name]} | {class_after[name]} | "
            f"{class_after[name] - class_before[name]:+d} |"
            for name in classes
        ],
        "",
        "## Exemplos de falsos mistos corrigidos",
        "",
        *_examples(mixed_corrected),
        "",
        "## Exemplos de precedência universal corrigida",
        "",
        *_examples(universal_corrected),
        "",
        "## Exemplos de modelos `Unknown_*`",
        "",
        *_examples(unknown_models),
        "",
        "## Possíveis regressões para auditoria",
        "",
        "### Novos casos mistos",
        "",
        *_examples(new_mixed),
        "",
        "### Universais que deixaram de ser universais",
        "",
        *_examples(lost_universal),
        "",
        "Relatório gerado deterministicamente a partir dos artefatos v2 e v3.",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "records": len(common),
        "mixed_corrected": len(mixed_corrected),
        "universal_corrected": len(universal_corrected),
        "unknown_models": len(unknown_models),
        "new_mixed": len(new_mixed),
        "lost_universal": len(lost_universal),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            generate_comparison(arguments.v2, arguments.v3, arguments.output),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
