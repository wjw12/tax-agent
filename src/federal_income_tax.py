"""Deterministic 2025 federal income tax helpers for validation."""

from __future__ import annotations

from decimal import Decimal

from .core import to_decimal
from .form_1040_tax_2025 import (
    compute_ordinary_income_tax_from_irs_2025,
    qdcg_fifteen_rate_threshold_2025,
    qdcg_zero_rate_threshold_2025,
)


def compute_ordinary_income_tax_2025(filing_status: str, taxable_income: Decimal | int | float | str) -> Decimal:
    return compute_ordinary_income_tax_from_irs_2025(filing_status, taxable_income)


def compute_form_1040_tax_2025(
    filing_status: str,
    taxable_income: Decimal | int | float | str,
    *,
    qualified_dividends: Decimal | int | float | str = Decimal("0"),
    capital_gain_distributions: Decimal | int | float | str = Decimal("0"),
    schedule_d_line_15: Decimal | int | float | str = Decimal("0"),
    schedule_d_line_16: Decimal | int | float | str = Decimal("0"),
    uses_form_2555: bool = False,
    requires_schedule_d_tax_worksheet: bool = False,
) -> Decimal:
    """Compute TY2025 Form 1040 line 16 for the standard QDCG path.

    This helper supports the ordinary-bracket path and the standard Qualified
    Dividends and Capital Gain Tax Worksheet path. It intentionally rejects
    cases that require the Foreign Earned Income Tax Worksheet or the more
    complex Schedule D Tax Worksheet.
    """

    line_1 = max(Decimal("0"), to_decimal(taxable_income).quantize(Decimal("0.01")))
    if line_1 == Decimal("0"):
        return Decimal("0.00")

    if uses_form_2555:
        raise ValueError("Form 2555 cases require the Foreign Earned Income Tax Worksheet")
    if requires_schedule_d_tax_worksheet:
        raise ValueError("This case requires the Schedule D Tax Worksheet")

    line_2 = max(Decimal("0"), to_decimal(qualified_dividends).quantize(Decimal("0.01")))
    line_15 = to_decimal(schedule_d_line_15).quantize(Decimal("0.01"))
    line_16 = to_decimal(schedule_d_line_16).quantize(Decimal("0.01"))

    if line_15 > Decimal("0") and line_16 > Decimal("0"):
        line_3 = min(line_15, line_16)
    else:
        line_3 = max(Decimal("0"), to_decimal(capital_gain_distributions).quantize(Decimal("0.01")))

    if line_2 == Decimal("0") and line_3 == Decimal("0"):
        return compute_ordinary_income_tax_2025(filing_status, line_1)

    line_4 = line_2 + line_3
    line_5 = max(Decimal("0"), line_1 - line_4)
    line_6 = qdcg_zero_rate_threshold_2025(filing_status)
    line_7 = min(line_1, line_6)
    line_8 = min(line_5, line_7)
    line_9 = line_7 - line_8
    line_10 = min(line_1, line_4)
    line_11 = line_9
    line_12 = max(Decimal("0"), line_10 - line_11)
    line_13 = qdcg_fifteen_rate_threshold_2025(filing_status)
    line_14 = min(line_1, line_13)
    line_15b = line_5 + line_9
    line_16b = max(Decimal("0"), line_14 - line_15b)
    line_17 = min(line_12, line_16b)
    line_18 = line_17 * Decimal("0.15")
    line_19 = line_9 + line_17
    line_20 = max(Decimal("0"), line_10 - line_19)
    line_21 = line_20 * Decimal("0.20")
    line_22 = compute_ordinary_income_tax_2025(filing_status, line_5)
    line_23 = line_18 + line_21 + line_22
    line_24 = compute_ordinary_income_tax_2025(filing_status, line_1)
    return min(line_23, line_24).quantize(Decimal("0.01"))
