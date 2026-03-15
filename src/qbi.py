"""Executable helpers for TY2025 QBI form selection, assembly, and validation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .core import to_decimal
from .models import (
    Form8995AInput,
    Form8995Input,
    QbiBusiness,
    QbiComplexBusiness,
    ScheduleCInput,
    ScheduleSEInput,
)
from .processors import process_8995, process_8995_a, process_schedule_c, process_schedule_se

QBI_SIMPLIFIED_THRESHOLD_MFJ_2025 = Decimal("394600")
QBI_SIMPLIFIED_THRESHOLD_OTHER_2025 = Decimal("197300")
QBI_FORM_CODE = Literal["8995", "8995-A"]


def _money(value: Decimal | int | float | str) -> Decimal:
    return to_decimal(value).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class QbiBusinessAssembly:
    business_name: str
    schedule_c_net_profit: Decimal | int | float | str
    deductible_half_se_tax: Decimal | int | float | str = Decimal("0")
    irc_224_deducted_qualified_tips: Decimal | int | float | str = Decimal("0")
    reit_ptp_income: Decimal | int | float | str = Decimal("0")
    w2_wages: Decimal | int | float | str = Decimal("0")
    ubia_of_qualified_property: Decimal | int | float | str = Decimal("0")


def qbi_simplified_threshold_2025(filing_status: str) -> Decimal:
    if filing_status == "married_filing_jointly":
        return QBI_SIMPLIFIED_THRESHOLD_MFJ_2025
    return QBI_SIMPLIFIED_THRESHOLD_OTHER_2025


def select_qbi_form_code_2025(
    filing_status: str,
    taxable_income_before_qbi: Decimal | int | float | str,
) -> Literal["8995", "8995-A"]:
    taxable_income = to_decimal(taxable_income_before_qbi)
    threshold = qbi_simplified_threshold_2025(filing_status)
    return "8995" if taxable_income <= threshold else "8995-A"


def compute_taxable_income_before_qbi(
    *,
    agi: Decimal | int | float | str,
    standard_deduction: Decimal | int | float | str = Decimal("0"),
    itemized_deductions: Decimal | int | float | str = Decimal("0"),
) -> Decimal:
    deduction = max(to_decimal(standard_deduction), to_decimal(itemized_deductions))
    return _money(max(Decimal("0"), to_decimal(agi) - deduction))


def build_qbi_business_assembly_from_forms(
    schedule_c: ScheduleCInput,
    schedule_se: ScheduleSEInput | None = None,
    *,
    irc_224_deducted_qualified_tips: Decimal | int | float | str = Decimal("0"),
    reit_ptp_income: Decimal | int | float | str = Decimal("0"),
    w2_wages: Decimal | int | float | str = Decimal("0"),
    ubia_of_qualified_property: Decimal | int | float | str = Decimal("0"),
) -> QbiBusinessAssembly:
    schedule_c_result = process_schedule_c(schedule_c)
    deductible_half_se_tax = Decimal("0")
    if schedule_se is not None:
        deductible_half_se_tax = _money(process_schedule_se(schedule_se).get_line("13"))
    return QbiBusinessAssembly(
        business_name=schedule_c.business_name,
        schedule_c_net_profit=_money(schedule_c_result.get_line("31")),
        deductible_half_se_tax=deductible_half_se_tax,
        irc_224_deducted_qualified_tips=irc_224_deducted_qualified_tips,
        reit_ptp_income=reit_ptp_income,
        w2_wages=w2_wages,
        ubia_of_qualified_property=ubia_of_qualified_property,
    )


def compute_qualified_business_income(source: QbiBusinessAssembly) -> Decimal:
    return _money(
        to_decimal(source.schedule_c_net_profit)
        - to_decimal(source.deductible_half_se_tax)
        - to_decimal(source.irc_224_deducted_qualified_tips)
    )


def build_qbi_business(source: QbiBusinessAssembly) -> QbiBusiness:
    return QbiBusiness(
        business_name=source.business_name,
        qualified_business_income=compute_qualified_business_income(source),
        reit_ptp_income=to_decimal(source.reit_ptp_income),
    )


def build_qbi_complex_business(source: QbiBusinessAssembly) -> QbiComplexBusiness:
    return QbiComplexBusiness(
        business_name=source.business_name,
        qualified_business_income=compute_qualified_business_income(source),
        w2_wages=to_decimal(source.w2_wages),
        ubia_of_qualified_property=to_decimal(source.ubia_of_qualified_property),
    )


def build_qbi_form_input_2025(
    *,
    filing_status: str,
    agi: Decimal | int | float | str,
    standard_deduction: Decimal | int | float | str = Decimal("0"),
    itemized_deductions: Decimal | int | float | str = Decimal("0"),
    net_capital_gains: Decimal | int | float | str = Decimal("0"),
    businesses: list[QbiBusinessAssembly],
) -> Form8995Input | Form8995AInput:
    taxable_income_before_qbi = compute_taxable_income_before_qbi(
        agi=agi,
        standard_deduction=standard_deduction,
        itemized_deductions=itemized_deductions,
    )
    form_code = select_qbi_form_code_2025(filing_status, taxable_income_before_qbi)
    net_capital_gains_decimal = to_decimal(net_capital_gains)
    if form_code == "8995":
        return Form8995Input(
            businesses=[build_qbi_business(source) for source in businesses],
            taxable_income_before_qbi=taxable_income_before_qbi,
            net_capital_gains=_money(net_capital_gains_decimal),
        )
    return Form8995AInput(
        businesses=[build_qbi_complex_business(source) for source in businesses],
        taxable_income_before_qbi=taxable_income_before_qbi,
        net_capital_gains=_money(net_capital_gains_decimal),
    )


def validate_qbi_form_input_2025(
    payload: Form8995Input | Form8995AInput,
    *,
    filing_status: str,
    agi: Decimal | int | float | str,
    standard_deduction: Decimal | int | float | str = Decimal("0"),
    itemized_deductions: Decimal | int | float | str = Decimal("0"),
    net_capital_gains: Decimal | int | float | str = Decimal("0"),
    businesses: list[QbiBusinessAssembly] | None = None,
) -> list[str]:
    issues: list[str] = []
    expected_taxable_income = compute_taxable_income_before_qbi(
        agi=agi,
        standard_deduction=standard_deduction,
        itemized_deductions=itemized_deductions,
    )
    expected_form_code = select_qbi_form_code_2025(filing_status, expected_taxable_income)
    if payload.form_code != expected_form_code:
        issues.append(
            f"expected {expected_form_code} for taxable_income_before_qbi={expected_taxable_income} "
            f"under TY2025 threshold, found {payload.form_code}"
        )
    if _money(payload.taxable_income_before_qbi) != expected_taxable_income:
        issues.append(
            f"taxable_income_before_qbi expected {expected_taxable_income}, found "
            f"{payload.taxable_income_before_qbi}"
        )
    expected_net_capital_gains = _money(net_capital_gains)
    if _money(payload.net_capital_gains) != expected_net_capital_gains:
        issues.append(
            f"net_capital_gains expected {expected_net_capital_gains}, found {payload.net_capital_gains}"
        )
    if businesses is None:
        return issues

    expected_payload = build_qbi_form_input_2025(
        filing_status=filing_status,
        agi=agi,
        standard_deduction=standard_deduction,
        itemized_deductions=itemized_deductions,
        net_capital_gains=expected_net_capital_gains,
        businesses=businesses,
    )
    if len(payload.businesses) != len(expected_payload.businesses):
        issues.append(
            f"business entry count expected {len(expected_payload.businesses)}, found {len(payload.businesses)}"
        )
        return issues

    same_form_code = payload.form_code == expected_payload.form_code
    for index, expected_business in enumerate(expected_payload.businesses):
        actual_business = payload.businesses[index]
        if actual_business.business_name != expected_business.business_name:
            issues.append(
                f"businesses[{index}].business_name expected {expected_business.business_name!r}, "
                f"found {actual_business.business_name!r}"
            )
        if _money(actual_business.qualified_business_income) != _money(expected_business.qualified_business_income):
            issues.append(
                f"businesses[{index}].qualified_business_income expected "
                f"{expected_business.qualified_business_income}, found "
                f"{actual_business.qualified_business_income}"
            )
        if same_form_code and payload.form_code == "8995":
            actual_reit = getattr(actual_business, "reit_ptp_income")
            expected_reit = getattr(expected_business, "reit_ptp_income")
            if _money(actual_reit) != _money(expected_reit):
                issues.append(
                    f"businesses[{index}].reit_ptp_income expected {expected_reit}, found {actual_reit}"
                )
        if same_form_code and payload.form_code == "8995-A":
            actual_wages = getattr(actual_business, "w2_wages")
            expected_wages = getattr(expected_business, "w2_wages")
            if _money(actual_wages) != _money(expected_wages):
                issues.append(
                    f"businesses[{index}].w2_wages expected {expected_wages}, found {actual_wages}"
                )
            actual_ubia = getattr(actual_business, "ubia_of_qualified_property")
            expected_ubia = getattr(expected_business, "ubia_of_qualified_property")
            if _money(actual_ubia) != _money(expected_ubia):
                issues.append(
                    f"businesses[{index}].ubia_of_qualified_property expected {expected_ubia}, "
                    f"found {actual_ubia}"
                )

    if payload.form_code == "8995":
        actual_deduction = process_8995(payload).get_line("15")
    else:
        actual_deduction = process_8995_a(payload).get_line("26")
    if expected_payload.form_code == "8995":
        expected_deduction = process_8995(expected_payload).get_line("15")
    else:
        expected_deduction = process_8995_a(expected_payload).get_line("26")
    if _money(actual_deduction) != _money(expected_deduction):
        issues.append(
            f"QBI deduction expected {expected_deduction}, found {actual_deduction}"
        )
    return issues
