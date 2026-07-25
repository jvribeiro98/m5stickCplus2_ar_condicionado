"""Interface de linha de comando da normalização."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from .reports import analyze_reports, inspect_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.normalization",
        description="Gera propostas OpenIR sem alterar o inventário original.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analisa relatórios de inventário.")
    analyze.add_argument("--inventory", type=Path, default=Path("reports"))
    analyze.add_argument("--output", type=Path, default=Path("normalization"))

    inspect = subparsers.add_parser("inspect", help="Inspeciona propostas por caminho ou ID.")
    inspect.add_argument("query")
    inspect.add_argument("--output", type=Path, default=Path("normalization"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        summary = analyze_reports(args.inventory, args.output)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    matches = inspect_output(args.output, args.query)
    print(json.dumps(matches, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if matches else 1
