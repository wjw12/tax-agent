"""Deterministic 2025 ordinary-income tax helpers for validation."""

from __future__ import annotations

from decimal import Decimal

from .core import to_decimal


_BRACKETS_2025: dict[str, list[tuple[Decimal, Decimal]]] = {
    "single": [
        (Decimal("11925"), Decimal("0.10")),
        (Decimal("48475"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250525"), Decimal("0.32")),
        (Decimal("626350"), Decimal("0.35")),
    ],
    "married_filing_jointly": [
        (Decimal("23850"), Decimal("0.10")),
        (Decimal("96950"), Decimal("0.12")),
        (Decimal("206700"), Decimal("0.22")),
        (Decimal("394600"), Decimal("0.24")),
        (Decimal("501050"), Decimal("0.32")),
        (Decimal("751600"), Decimal("0.35")),
    ],
    "married_filing_separately": [
        (Decimal("11925"), Decimal("0.10")),
        (Decimal("48475"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250525"), Decimal("0.32")),
        (Decimal("375800"), Decimal("0.35")),
    ],
    "head_of_household": [
        (Decimal("17000"), Decimal("0.10")),
        (Decimal("64850"), Decimal("0.12")),
        (Decimal("103350"), Decimal("0.22")),
        (Decimal("197300"), Decimal("0.24")),
        (Decimal("250500"), Decimal("0.32")),
        (Decimal("626350"), Decimal("0.35")),
    ],
    "qualifying_surviving_spouse": [
        (Decimal("23850"), Decimal("0.10")),
        (Decimal("96950"), Decimal("0.12")),
        (Decimal("206700"), Decimal("0.22")),
        (Decimal("394600"), Decimal("0.24")),
        (Decimal("501050"), Decimal("0.32")),
        (Decimal("751600"), Decimal("0.35")),
    ],
}


def compute_ordinary_income_tax_2025(filing_status: str, taxable_income: Decimal | int | float | str) -> Decimal:
    income = max(Decimal("0"), to_decimal(taxable_income).quantize(Decimal("0.01")))
    brackets = _BRACKETS_2025[filing_status]
    prior_limit = Decimal("0")
    tax = Decimal("0")
    for limit, rate in brackets:
        if income <= prior_limit:
            break
        taxable_chunk = min(income, limit) - prior_limit
        tax += taxable_chunk * rate
        prior_limit = limit
    if income > prior_limit:
        tax += (income - prior_limit) * Decimal("0.37")
    return tax.quantize(Decimal("0.01"))
