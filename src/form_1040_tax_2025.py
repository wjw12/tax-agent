"""Load normalized TY2025 IRS Form 1040 tax data and compute ordinary tax."""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from .core import round_dollar, to_decimal


_DATA_DIR = Path(__file__).resolve().parent / "data" / "irs" / "2025" / "form_1040"
_TAX_TABLE_MAX_INCOME = 100000


def _coerce_decimal(value: Any) -> Decimal:
    return Decimal(str(value).replace(",", ""))


@lru_cache(maxsize=None)
def _load_json(filename: str) -> dict[str, Any]:
    return json.loads((_DATA_DIR / filename).read_text(encoding="utf-8"))


def load_tax_table_2025() -> dict[str, Any]:
    return _load_json("tax-table.json")


def load_tax_computation_worksheet_2025() -> dict[str, Any]:
    return _load_json("tax-computation-worksheet.json")


def load_qdcg_worksheet_metadata_2025() -> dict[str, Any]:
    return _load_json("qdcg-worksheet-metadata.json")


def load_schedule_d_tax_worksheet_metadata_2025() -> dict[str, Any]:
    return _load_json("schedule-d-tax-worksheet-metadata.json")


def _rounded_taxable_income(taxable_income: Decimal | int | float | str) -> int:
    rounded = round_dollar(max(Decimal("0"), to_decimal(taxable_income)))
    return int(rounded)


def lookup_tax_table_tax_2025(filing_status: str, taxable_income: Decimal | int | float | str) -> Decimal:
    rounded_income = _rounded_taxable_income(taxable_income)
    if rounded_income >= _TAX_TABLE_MAX_INCOME:
        raise ValueError("Tax table lookup only applies when rounded taxable income is below $100,000")

    rows = load_tax_table_2025()["filing_statuses"][filing_status]
    for row in rows:
        if row["income_min"] <= rounded_income < row["income_max"]:
            return _coerce_decimal(row["tax"]).quantize(Decimal("0.01"))
    raise ValueError(f"No TY2025 tax-table row matched taxable income {rounded_income} for {filing_status}")


def compute_tax_computation_worksheet_tax_2025(
    filing_status: str,
    taxable_income: Decimal | int | float | str,
) -> Decimal:
    rounded_income = _rounded_taxable_income(taxable_income)
    rows = load_tax_computation_worksheet_2025()["filing_statuses"][filing_status]
    for row in rows:
        income_max = row["income_max"]
        if rounded_income < row["income_min"]:
            continue
        if income_max is not None and rounded_income > income_max:
            continue
        rate = _coerce_decimal(row["rate"])
        subtraction_amount = _coerce_decimal(row["subtraction_amount"])
        return (Decimal(rounded_income) * rate - subtraction_amount).quantize(Decimal("0.01"))
    raise ValueError(
        f"No TY2025 tax-computation-worksheet row matched taxable income {rounded_income} for {filing_status}"
    )


def compute_ordinary_income_tax_from_irs_2025(
    filing_status: str,
    taxable_income: Decimal | int | float | str,
) -> Decimal:
    rounded_income = _rounded_taxable_income(taxable_income)
    if rounded_income <= 0:
        return Decimal("0.00")
    if rounded_income < _TAX_TABLE_MAX_INCOME:
        return lookup_tax_table_tax_2025(filing_status, rounded_income)
    return compute_tax_computation_worksheet_tax_2025(filing_status, rounded_income)


def qdcg_zero_rate_threshold_2025(filing_status: str) -> Decimal:
    thresholds = load_qdcg_worksheet_metadata_2025()["thresholds"]["line_6_zero_rate_threshold"]
    return _coerce_decimal(thresholds[filing_status])


def qdcg_fifteen_rate_threshold_2025(filing_status: str) -> Decimal:
    thresholds = load_qdcg_worksheet_metadata_2025()["thresholds"]["line_13_fifteen_rate_threshold"]
    return _coerce_decimal(thresholds[filing_status])
