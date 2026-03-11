"""Core result objects and shared helpers for deterministic form processing."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel, Field


def to_decimal(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def sum_decimals(values: list[Decimal] | tuple[Decimal, ...] | Any) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += to_decimal(value)
    return total


def round_dollar(value: Decimal) -> Decimal:
    rounded = to_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if rounded == Decimal("-0"):
        return Decimal("0")
    return rounded


def format_irs_dollar(value: Decimal) -> str:
    return str(int(round_dollar(value)))


def digits_only(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit())


class CalculationLine(BaseModel):
    line: str
    description: str
    value: Decimal
    formula: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FormComputation(BaseModel):
    form_code: str
    form_name: str
    lines: dict[str, CalculationLine] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_line(
        self,
        line: str,
        description: str,
        value: Decimal | int | float | str,
        formula: str | None = None,
        inputs: dict[str, Any] | None = None,
        notes: list[str] | None = None,
    ) -> None:
        self.lines[line] = CalculationLine(
            line=line,
            description=description,
            value=to_decimal(value),
            formula=formula,
            inputs=inputs or {},
            notes=notes or [],
        )

    def get_line(self, line: str) -> Decimal:
        calculation_line = self.lines.get(line)
        return calculation_line.value if calculation_line else Decimal("0")

