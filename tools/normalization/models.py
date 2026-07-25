"""Modelos internos; todos preservam os valores de entrada."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandRecord:
    original_name: str
    protocol: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class InventoryRecord:
    record_id: str
    source_path: str
    original_category: str | None
    original_brand: str | None
    original_model: str | None
    comments: tuple[str, ...] = ()
    commands: tuple[CommandRecord, ...] = ()
    signal_count: int = 0
    duplicate_count: int = 0
    parse_errors: tuple[str, ...] = ()
    source_report: str = "inventory"
    original_data: dict[str, Any] = field(default_factory=dict, compare=False)
