"""Logical field builders and PDF form fill helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject

from .audit_models import AuditStatus, FormAuditSidecar
from .core import FormComputation, digits_only, format_irs_dollar
from .models import (
    BaseFormInput,
    Form1040Input,
    Form1040NRScheduleAInput,
    Form1040NRScheduleNECInput,
    Form1040NRScheduleOIInput,
    Form1040NRInput,
    Form1040SRInput,
    Schedule1AInput,
    Form2441Input,
    Form4562Input,
    Form8862Input,
    Form8863Input,
    Form8889Input,
    Form8949Input,
    Form8962Input,
    Form8995AInput,
    Form8995Input,
    Form8829Input,
    Schedule1Input,
    Schedule2Input,
    Schedule3Input,
    Schedule8812Input,
    ScheduleAInput,
    ScheduleBInput,
    ScheduleCInput,
    ScheduleDInput,
    ScheduleEICInput,
    ScheduleEInput,
    ScheduleSEInput,
)
from .pdf_mapping import PdfFieldMapping
from .processors import (
    process_1040,
    process_1040_nr_schedule_a,
    process_1040_nr_schedule_nec,
    process_1040_nr_schedule_oi,
    process_1040_nr,
    process_1040_sr,
    process_2441,
    process_4562,
    process_8862,
    process_8863,
    process_8889,
    process_8949,
    process_8962,
    process_8995,
    process_8995_a,
    process_8812,
    process_8829,
    process_schedule_1_a,
    process_schedule_1,
    process_schedule_2,
    process_schedule_3,
    process_schedule_a,
    process_schedule_b,
    process_schedule_c,
    process_schedule_d,
    process_schedule_e,
    process_schedule_eic,
    process_schedule_se,
)

FORMS_DIR = Path(__file__).resolve().parent.parent / "2025-empty-forms"


@dataclass(frozen=True)
class PdfFillPlan:
    blank_pdf_path: Path
    pdf_filename: str
    logical_field_values: dict[str, str]
    mapping: PdfFieldMapping


@dataclass(frozen=True)
class PdfVerificationResult:
    status: Literal["verified", "failed"]
    mapped_text_count: int
    mapped_checkbox_count: int
    verified_count: int
    unmapped_keys: list[str]
    mismatches: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "mapped_text_count": self.mapped_text_count,
            "mapped_checkbox_count": self.mapped_checkbox_count,
            "verified_count": self.verified_count,
            "unmapped_keys": self.unmapped_keys,
            "mismatches": self.mismatches,
        }


@dataclass(frozen=True)
class RenderedPdfResult:
    form_code: str
    pdf_filename: str
    output_pdf_path: Path
    verification: PdfVerificationResult
    payload_path: Path | None = None
    audit_path: Path | None = None
    audit_status: AuditStatus | None = None


@dataclass(frozen=True)
class PdfFillRunResult:
    run_id: str
    run_dir: Path
    manifest_path: Path
    verification_report_path: Path
    status: Literal["verified", "draft"]
    forms: list[RenderedPdfResult]


def _line_fields(form: FormComputation) -> dict[str, str]:
    fields = {f"line_{line_id}": format_irs_dollar(line.value) for line_id, line in form.lines.items()}
    for key, value in form.metadata.items():
        if isinstance(value, bool):
            fields[f"meta_{key}"] = "yes" if value else "no"
        elif isinstance(value, list):
            fields[f"meta_{key}"] = "; ".join(str(item) for item in value)
        else:
            fields[f"meta_{key}"] = str(value)
    return fields


def _taxpayer_identifying_number(data: Form1040Input | Form1040SRInput | Form1040NRInput) -> str:
    return digits_only(data.taxpayer.identifying_number or data.taxpayer.ssn)


def _identity_fields(data: Form1040Input | Form1040SRInput) -> dict[str, str]:
    fields = {
        "taxpayer_first_name": data.taxpayer.first_name,
        "taxpayer_last_name": data.taxpayer.last_name,
        "taxpayer_ssn": _taxpayer_identifying_number(data),
        "taxpayer_address_line1": data.taxpayer.address.line1,
        "taxpayer_address_line2": data.taxpayer.address.line2 or "",
        "taxpayer_city": data.taxpayer.address.city,
        "taxpayer_state": data.taxpayer.address.state,
        "taxpayer_postal_code": data.taxpayer.address.postal_code,
        "taxpayer_foreign_country": data.taxpayer.address.country or "",
        "filing_status": data.filing_status,
        "digital_assets": "yes" if data.digital_assets else "no",
    }
    if data.spouse:
        fields.update(
            {
                "spouse_first_name": data.spouse.first_name,
                "spouse_last_name": data.spouse.last_name,
                "spouse_ssn": digits_only(data.spouse.identifying_number or data.spouse.ssn),
            }
        )
    return fields


def _identity_fields_1040_nr(data: Form1040NRInput) -> dict[str, str]:
    fields = {
        "taxpayer_first_name": data.taxpayer.first_name,
        "taxpayer_last_name": data.taxpayer.last_name,
        "taxpayer_ssn": _taxpayer_identifying_number(data),
        "taxpayer_address_line1": data.taxpayer.address.line1,
        "taxpayer_address_line2": data.taxpayer.address.line2 or "",
        "taxpayer_city": data.taxpayer.address.city,
        "taxpayer_state": data.taxpayer.address.state,
        "taxpayer_postal_code": data.taxpayer.address.postal_code,
        "taxpayer_foreign_country": data.taxpayer.address.country or "",
        "taxpayer_foreign_province": data.taxpayer.address.state if data.taxpayer.address.country else "",
        "taxpayer_foreign_postal_code": data.taxpayer.address.postal_code if data.taxpayer.address.country else "",
        "filing_status": data.filing_status,
        "digital_assets": "yes" if data.digital_assets else "no",
        "qualifying_person_name": data.qualifying_person_name or "",
    }
    if data.taxpayer.address.country:
        fields["taxpayer_state"] = ""
        fields["taxpayer_postal_code"] = ""
    return fields


def _full_name(first_name: str, last_name: str) -> str:
    return " ".join(part for part in (first_name, last_name) if part).strip()


def _mmddyyyy(value) -> str:
    if value is None:
        return ""
    return value.strftime("%m/%d/%Y")


def _mmdd_parts(value) -> tuple[str, str]:
    if value is None:
        return "", ""
    return f"{value.month:02d}", f"{value.day:02d}"


def _year_digits(value) -> tuple[str, str, str, str]:
    if value is None:
        return "", "", "", ""
    year = f"{value.year:04d}"
    return year[0], year[1], year[2], year[3]


def _days_lived_in_year(months_lived_with_taxpayer: int, tax_year: int) -> int:
    if months_lived_with_taxpayer >= 12:
        return 366 if tax_year % 4 == 0 and (tax_year % 100 != 0 or tax_year % 400 == 0) else 365
    if months_lived_with_taxpayer <= 0:
        return 0
    average_days = 30.4
    return int(round(months_lived_with_taxpayer * average_days))


def _blank_if_none(value: object | None) -> str:
    return "" if value is None else str(value)


def _credit_claims_8862(data: Form8862Input) -> set[str]:
    if data.credit_claims:
        return set(data.credit_claims)
    if data.credit_type == "eic":
        return {"eic"}
    if data.credit_type in {"ctc", "odc"}:
        return {"ctc_odc"}
    return {"aotc"}


def fill_1040_fields(data: Form1040Input) -> dict[str, str]:
    return {**_identity_fields(data), **_line_fields(process_1040(data))}


def fill_1040_sr_fields(data: Form1040SRInput) -> dict[str, str]:
    return {**_identity_fields(data), **_line_fields(process_1040_sr(data))}


def fill_1040_nr_fields(data: Form1040NRInput) -> dict[str, str]:
    return {**_identity_fields_1040_nr(data), **_line_fields(process_1040_nr(data))}


def fill_1040_nr_schedule_oi_fields(data: Form1040NRScheduleOIInput) -> dict[str, str]:
    form = process_1040_nr_schedule_oi(data)
    fields = {
        "return_name": data.return_name,
        "return_identifying_number": digits_only(data.return_identifying_number),
        "citizenship_countries": data.citizenship_countries,
        "tax_residence_country": data.tax_residence_country,
        "visa_type": data.visa_type,
        "visa_status_change_details": data.visa_status_change_details,
        "days_in_us_2023": str(data.days_in_us_2023),
        "days_in_us_2024": str(data.days_in_us_2024),
        "days_in_us_2025": str(data.days_in_us_2025),
        "prior_filing_year_and_form": data.prior_filing_year_and_form,
        "treaty_total_exempt_income": format_irs_dollar(form.get_line("l1e")),
    }
    for index in range(8):
        trip = data.entry_departure_dates[index] if index < len(data.entry_departure_dates) else None
        slot = index + 1
        fields[f"entry_{slot}_date_entered"] = _mmddyyyy(trip.date_entered if trip else None)
        fields[f"entry_{slot}_date_departed"] = _mmddyyyy(trip.date_departed if trip else None)
    for index in range(3):
        claim = data.treaty_claims[index] if index < len(data.treaty_claims) else None
        slot = index + 1
        fields[f"treaty_claim_{slot}_country"] = claim.country if claim else ""
        fields[f"treaty_claim_{slot}_article"] = claim.treaty_article if claim else ""
        fields[f"treaty_claim_{slot}_months"] = str(claim.months_claimed_in_prior_years) if claim else ""
        fields[f"treaty_claim_{slot}_exempt_income"] = (
            format_irs_dollar(claim.current_year_exempt_income) if claim else ""
        )

    yes_no_fields = {
        "applied_for_green_card": data.applied_for_green_card,
        "was_us_citizen": data.was_us_citizen,
        "was_green_card_holder": data.was_green_card_holder,
        "changed_visa_status": data.changed_visa_status,
        "previously_filed_us_return": data.previously_filed_us_return,
        "filing_for_trust": data.filing_for_trust,
        "trust_had_us_or_foreign_owner_or_distribution": data.trust_had_us_or_foreign_owner_or_distribution,
        "received_total_compensation_over_250k": data.received_total_compensation_over_250k,
        "used_alternative_compensation_sourcing_method": data.used_alternative_compensation_sourcing_method,
        "taxed_on_treaty_exempt_income_in_foreign_country": data.taxed_on_treaty_exempt_income_in_foreign_country,
        "claiming_competent_authority_benefits": data.claiming_competent_authority_benefits,
    }
    fields.update({key: "yes" if value else "no" for key, value in yes_no_fields.items()})
    if data.commuter_from_canada:
        fields["commuter_from_canada"] = "yes"
    if data.commuter_from_mexico:
        fields["commuter_from_mexico"] = "yes"
    if data.real_property_election_first_year:
        fields["real_property_election_first_year"] = "yes"
    if data.real_property_election_continuing:
        fields["real_property_election_continuing"] = "yes"
    return fields


def fill_1040_nr_schedule_a_fields(data: Form1040NRScheduleAInput) -> dict[str, str]:
    return {
        "return_name": data.return_name,
        "return_identifying_number": digits_only(data.return_identifying_number),
        "other_itemized_deduction_description": data.other_itemized_deduction_description,
        **_line_fields(process_1040_nr_schedule_a(data)),
    }


def fill_schedule_1_a_fields(data: Schedule1AInput) -> dict[str, str]:
    form = process_schedule_1_a(data)
    entry_one = data.vehicle_loan_interest_entries[0] if data.vehicle_loan_interest_entries else None
    entry_two = data.vehicle_loan_interest_entries[1] if len(data.vehicle_loan_interest_entries) > 1 else None
    return {
        "return_name": data.return_name,
        "return_identifying_number": digits_only(data.return_identifying_number),
        "line_14a": format_irs_dollar(data.qualified_overtime_w2),
        "line_14b": format_irs_dollar(data.qualified_overtime_1099),
        "vehicle_1_vin": entry_one.vin if entry_one else "",
        "vehicle_1_interest_deducted_elsewhere": (
            format_irs_dollar(entry_one.interest_deducted_elsewhere) if entry_one else ""
        ),
        "vehicle_1_interest_for_schedule_1a": (
            format_irs_dollar(entry_one.interest_for_schedule_1a) if entry_one else ""
        ),
        "vehicle_2_vin": entry_two.vin if entry_two else "",
        "vehicle_2_interest_deducted_elsewhere": (
            format_irs_dollar(entry_two.interest_deducted_elsewhere) if entry_two else ""
        ),
        "vehicle_2_interest_for_schedule_1a": (
            format_irs_dollar(entry_two.interest_for_schedule_1a) if entry_two else ""
        ),
        **_line_fields(form),
    }


def fill_1040_nr_schedule_nec_fields(data: Form1040NRScheduleNECInput) -> dict[str, str]:
    form = process_1040_nr_schedule_nec(data)
    fields = {
        "return_name": data.return_name,
        "return_identifying_number": digits_only(data.return_identifying_number),
    }
    percent = f"{int(data.other_rate_percent):02d}" if data.other_rate_percent else "00"
    fields["other_rate_percent_tens"] = percent[0]
    fields["other_rate_percent_ones"] = percent[1]

    row_prefixes = {
        "dividends_us_corp": "row_1a",
        "dividends_foreign_corp": "row_1b",
        "dividend_equivalent": "row_1c",
        "interest_mortgage": "row_2a",
        "interest_foreign_corp": "row_2b",
        "interest_other": "row_2c",
        "industrial_royalties": "row_3",
        "motion_picture_royalties": "row_4",
        "other_royalties": "row_5",
        "real_property_royalties": "row_6",
        "pensions": "row_7",
        "social_security": "row_8",
        "gambling_canada": "row_10",
        "gambling_other": "row_11",
        "other": "row_12",
    }
    rows_by_category = {row.category: row for row in data.income_rows}
    for category, prefix in row_prefixes.items():
        row = rows_by_category.get(category)
        if category == "gambling_canada":
            fields[f"{prefix}_winnings"] = format_irs_dollar(row.winnings) if row else ""
            fields[f"{prefix}_losses"] = format_irs_dollar(row.losses) if row else ""
        if category == "other":
            description = row.description or "" if row else ""
            fields[f"{prefix}_description_line_1"] = description[:22]
            fields[f"{prefix}_description_line_2"] = description[22:44]
        fields[f"{prefix}_10"] = format_irs_dollar(row.amount_at_10_percent) if row else ""
        fields[f"{prefix}_15"] = format_irs_dollar(row.amount_at_15_percent) if row else ""
        fields[f"{prefix}_30"] = format_irs_dollar(row.amount_at_30_percent) if row else ""

    capital_gain = form.get_line("18")
    if capital_gain:
        fields[f"row_9_{data.capital_gain_rate_class}"] = format_irs_dollar(capital_gain)

    for index in range(5):
        tx = data.capital_transactions[index] if index < len(data.capital_transactions) else None
        slot = index + 1
        prefix = f"capital_tx_{slot}"
        if tx:
            delta = tx.proceeds - tx.cost_basis
            fields[f"{prefix}_description"] = tx.description
            fields[f"{prefix}_date_acquired"] = _mmddyyyy(tx.date_acquired)
            fields[f"{prefix}_date_sold"] = _mmddyyyy(tx.date_sold)
            fields[f"{prefix}_sales_price"] = format_irs_dollar(tx.proceeds)
            fields[f"{prefix}_cost_basis"] = format_irs_dollar(tx.cost_basis)
            fields[f"{prefix}_loss"] = format_irs_dollar(-delta) if delta < 0 else ""
            fields[f"{prefix}_gain"] = format_irs_dollar(delta) if delta > 0 else ""
        else:
            fields[f"{prefix}_description"] = ""
            fields[f"{prefix}_date_acquired"] = ""
            fields[f"{prefix}_date_sold"] = ""
            fields[f"{prefix}_sales_price"] = ""
            fields[f"{prefix}_cost_basis"] = ""
            fields[f"{prefix}_loss"] = ""
            fields[f"{prefix}_gain"] = ""

    fields["line_13a"] = format_irs_dollar(form.get_line("13a"))
    fields["line_13b"] = format_irs_dollar(form.get_line("13b"))
    fields["line_13c"] = format_irs_dollar(form.get_line("13c"))
    fields["line_14a"] = format_irs_dollar(form.get_line("14a"))
    fields["line_14b"] = format_irs_dollar(form.get_line("14b"))
    fields["line_14c"] = format_irs_dollar(form.get_line("14c"))
    fields["line_15"] = format_irs_dollar(form.get_line("15"))
    fields["line_17f"] = format_irs_dollar(form.get_line("17f"))
    fields["line_17g"] = format_irs_dollar(form.get_line("17g"))
    fields["line_18"] = format_irs_dollar(form.get_line("18"))
    for key, value in form.metadata.items():
        fields[f"meta_{key}"] = str(value)
    return fields


def fill_schedule_1_fields(data: Schedule1Input) -> dict[str, str]:
    return _line_fields(process_schedule_1(data))


def fill_schedule_2_fields(data: Schedule2Input) -> dict[str, str]:
    return _line_fields(process_schedule_2(data))


def fill_schedule_3_fields(data: Schedule3Input) -> dict[str, str]:
    return _line_fields(process_schedule_3(data))


def fill_schedule_a_fields(data: ScheduleAInput) -> dict[str, str]:
    return _line_fields(process_schedule_a(data))


def fill_schedule_b_fields(data: ScheduleBInput) -> dict[str, str]:
    return _line_fields(process_schedule_b(data))


def fill_schedule_d_fields(data: ScheduleDInput) -> dict[str, str]:
    return _line_fields(process_schedule_d(data))


def fill_8949_fields(data: Form8949Input) -> dict[str, str]:
    form = process_8949(data)
    return {
        "short_term_total": format_irs_dollar(form.get_line("short_gain")),
        "long_term_total": format_irs_dollar(form.get_line("long_gain")),
        "meta_transaction_count": str(form.metadata.get("transaction_count", 0)),
    }


def fill_schedule_c_fields(data: ScheduleCInput) -> dict[str, str]:
    return _line_fields(process_schedule_c(data))


def fill_schedule_se_fields(data: ScheduleSEInput) -> dict[str, str]:
    return _line_fields(process_schedule_se(data))


def fill_4562_fields(data: Form4562Input) -> dict[str, str]:
    return _line_fields(process_4562(data))


def fill_8829_fields(data: Form8829Input) -> dict[str, str]:
    return _line_fields(process_8829(data))


def fill_8995_fields(data: Form8995Input) -> dict[str, str]:
    return _line_fields(process_8995(data))


def fill_8995_a_fields(data: Form8995AInput) -> dict[str, str]:
    return _line_fields(process_8995_a(data))


def fill_schedule_e_fields(data: ScheduleEInput) -> dict[str, str]:
    return _line_fields(process_schedule_e(data))


def fill_8812_fields(data: Schedule8812Input) -> dict[str, str]:
    return _line_fields(process_8812(data))


def fill_schedule_eic_fields(data: ScheduleEICInput) -> dict[str, str]:
    fields = {
        "return_name": data.return_name,
        "return_ssn": digits_only(data.return_ssn),
    }
    for index in range(3):
        child = data.qualifying_children[index] if index < len(data.qualifying_children) else None
        slot = index + 1
        fields[f"child_{slot}_name"] = _full_name(child.first_name, child.last_name) if child else ""
        fields[f"child_{slot}_ssn"] = digits_only(child.ssn) if child else ""
        for digit_index, digit in enumerate(_year_digits(child.date_of_birth if child else None), start=1):
            fields[f"child_{slot}_birth_year_digit_{digit_index}"] = digit
        fields[f"child_{slot}_relationship"] = child.relationship if child else ""
        fields[f"child_{slot}_months_lived"] = str(child.months_lived_with_taxpayer) if child else ""
        if child:
            fields[f"child_{slot}_student_status"] = "yes" if child.is_student else "no"
            fields[f"child_{slot}_disability_status"] = (
                "yes" if child.permanently_totally_disabled else "no"
            )
    return fields


def fill_2441_fields(data: Form2441Input) -> dict[str, str]:
    return _line_fields(process_2441(data))


def fill_8863_fields(data: Form8863Input) -> dict[str, str]:
    return _line_fields(process_8863(data))


def fill_8889_fields(data: Form8889Input) -> dict[str, str]:
    return _line_fields(process_8889(data))


def fill_8962_fields(data: Form8962Input) -> dict[str, str]:
    form = process_8962(data)
    return {
        "line_27": format_irs_dollar(form.get_line("24")),
        "line_28": format_irs_dollar(form.get_line("25")),
        "line_29": format_irs_dollar(form.get_line("29")),
    }


def fill_8862_fields(data: Form8862Input) -> dict[str, str]:
    claims = _credit_claims_8862(data)
    fields = {
        "return_name": data.return_name,
        "return_ssn": digits_only(data.return_ssn),
        "filing_tax_year": str(data.tax_year),
        "part_ii_line_3": "yes" if data.part_ii_only_income_or_investment_income_issue else "no",
        "part_ii_line_4": (
            "yes" if data.part_ii_taxpayer_or_spouse_can_be_claimed_as_qualifying_child else "no"
        ),
        "part_ii_line_6": "yes" if data.qualifying_children else "no",
    }
    if "eic" in claims:
        fields["claim_eic"] = "yes"
    if "ctc_odc" in claims:
        fields["claim_ctc_odc"] = "yes"
    if "aotc" in claims:
        fields["claim_aotc"] = "yes"

    for index in range(3):
        child = data.qualifying_children[index] if index < len(data.qualifying_children) else None
        slot = index + 1
        fields[f"part_ii_child_{slot}_name"] = _full_name(child.first_name, child.last_name) if child else ""
        fields[f"part_ii_child_{slot}_days_lived"] = (
            str(child.days_lived_with_taxpayer_in_us or _days_lived_in_year(child.months_lived_with_taxpayer, data.tax_year))
            if child
            else ""
        )
        birth_month, birth_day = _mmdd_parts(child.date_of_birth if child else None)
        death_month, death_day = _mmdd_parts(child.date_of_death if child else None)
        fields[f"part_ii_child_{slot}_birth_month"] = birth_month
        fields[f"part_ii_child_{slot}_birth_day"] = birth_day
        fields[f"part_ii_child_{slot}_death_month"] = death_month
        fields[f"part_ii_child_{slot}_death_day"] = death_day

    section_b = data.part_ii_section_b
    fields["part_ii_section_b_line_9a"] = _blank_if_none(
        section_b.taxpayer_main_home_days_in_us if section_b else None
    )
    fields["part_ii_section_b_line_9b"] = _blank_if_none(
        section_b.spouse_main_home_days_in_us if section_b else None
    )
    fields["part_ii_section_b_line_10a"] = _blank_if_none(section_b.taxpayer_age if section_b else None)
    fields["part_ii_section_b_line_10b"] = _blank_if_none(section_b.spouse_age if section_b else None)
    if section_b and section_b.taxpayer_can_be_claimed_as_dependent is not None:
        fields["part_ii_section_b_line_11a"] = (
            "yes" if section_b.taxpayer_can_be_claimed_as_dependent else "no"
        )
    if section_b and section_b.spouse_can_be_claimed_as_dependent is not None:
        fields["part_ii_section_b_line_11b"] = "yes" if section_b.spouse_can_be_claimed_as_dependent else "no"

    for index in range(4):
        child = data.ctc_children[index] if index < len(data.ctc_children) else None
        slot = index + 1
        fields[f"part_iii_child_{slot}_name"] = child.name if child else ""
        if child:
            fields[f"part_iii_line_14_child_{slot}"] = (
                "yes" if child.lived_with_you_more_than_half_year else "no"
            )
            fields[f"part_iii_line_15_child_{slot}"] = "yes" if child.qualifies_for_credit else "no"
            fields[f"part_iii_line_16_child_{slot}"] = "yes" if child.is_dependent else "no"
            fields[f"part_iii_line_17_child_{slot}"] = (
                "yes" if child.is_us_citizen_national_or_resident else "no"
            )

    for index in range(4):
        dependent = data.odc_dependents[index] if index < len(data.odc_dependents) else None
        slot = index + 1
        fields[f"part_iii_other_dependent_{slot}_name"] = dependent.name if dependent else ""
        if dependent:
            fields[f"part_iii_line_16_other_dependent_{slot}"] = (
                "yes" if dependent.is_dependent else "no"
            )
            fields[f"part_iii_line_17_other_dependent_{slot}"] = (
                "yes" if dependent.is_us_citizen_national_or_resident else "no"
            )

    for index in range(3):
        student = data.aotc_students[index] if index < len(data.aotc_students) else None
        slot = index + 1
        fields[f"part_iv_student_{slot}_name"] = student.name if student else ""
        if student:
            fields[f"part_iv_line_19a_student_{slot}"] = (
                "yes" if student.is_eligible_student else "no"
            )
            fields[f"part_iv_line_19b_student_{slot}"] = (
                "yes" if student.hope_or_aotc_claimed_for_any_4_prior_years else "no"
            )

    return fields


def list_pdf_fields(pdf_path: str | Path) -> dict[str, object]:
    reader = PdfReader(str(pdf_path))
    return reader.get_fields() or {}


def build_pdf_fill_plan(payload) -> PdfFillPlan:
    """Build the canonical logical-field and PDF-field mapping plan for a payload."""

    from .pdf_mapping import build_pdf_field_mapping
    from .registry import build_field_values, get_form_definition

    definition = get_form_definition(payload.form_code)
    logical_field_values = build_field_values(payload)
    mapping = build_pdf_field_mapping(
        payload.form_code,
        definition.pdf_filename,
        logical_field_values,
    )
    return PdfFillPlan(
        blank_pdf_path=FORMS_DIR / definition.pdf_filename,
        pdf_filename=definition.pdf_filename,
        logical_field_values=logical_field_values,
        mapping=mapping,
    )


def write_mapped_pdf(
    blank_pdf_path: str | Path,
    output_pdf_path: str | Path,
    mapping: PdfFieldMapping,
) -> Path:
    """Write a PDF using an already-built PdfFieldMapping."""

    reader = PdfReader(str(blank_pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    acroform = writer._root_object.get("/AcroForm")
    if acroform and hasattr(acroform, "get_object"):
        acroform = acroform.get_object()
        acroform[NameObject("/NeedAppearances")] = BooleanObject(True)
    for page in writer.pages:
        annots = page.get("/Annots", [])
        if hasattr(annots, "get_object"):
            annots = annots.get_object()
        for annot_ref in annots:
            annot = annot_ref.get_object()
            field_name = annot.get("/T")
            if field_name in mapping.mapped_text_fields:
                value = TextStringObject(mapping.mapped_text_fields[field_name])
                annot[NameObject("/V")] = value
                annot[NameObject("/DV")] = value
                continue
            if field_name in mapping.mapped_checkbox_fields:
                _, on_value = mapping.mapped_checkbox_fields[field_name]
                value = NameObject(on_value)
                annot[NameObject("/V")] = value
                annot[NameObject("/AS")] = value
                annot[NameObject("/DV")] = value
    output_path = Path(output_pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def load_payload_for_pdf_fill(
    payload_path: str | Path,
    *,
    validation_mode: Literal["reference", "live"] = "live",
) -> BaseFormInput:
    """Load and validate one saved payload JSON file through the registry model path."""

    from .registry import parse_form_input

    resolved = Path(payload_path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    form_code = payload.get("form_code")
    if not form_code:
        raise ValueError(f"Payload at {resolved} is missing form_code")
    return parse_form_input(form_code, payload, validation_mode=validation_mode)


def verify_mapped_pdf(
    output_pdf_path: str | Path,
    mapping: PdfFieldMapping,
) -> PdfVerificationResult:
    """Reopen a rendered PDF and verify every mapped text and checkbox field."""

    text_values, checkbox_values = _read_written_pdf_values(output_pdf_path)
    mismatches: list[str] = []
    verified_count = 0

    for field_name, expected in mapping.mapped_text_fields.items():
        actual = text_values.get(field_name, "")
        if actual != expected:
            mismatches.append(
                f"{field_name}: expected {expected!r}, got {actual!r}"
            )
            continue
        verified_count += 1

    for field_name, (_, on_value) in mapping.mapped_checkbox_fields.items():
        actual = checkbox_values.get(field_name, "")
        if actual != on_value:
            mismatches.append(
                f"{field_name}: expected {on_value!r}, got {actual!r}"
            )
            continue
        verified_count += 1

    status: Literal["verified", "failed"] = (
        "verified" if not mapping.unmapped_keys and not mismatches else "failed"
    )
    return PdfVerificationResult(
        status=status,
        mapped_text_count=len(mapping.mapped_text_fields),
        mapped_checkbox_count=len(mapping.mapped_checkbox_fields),
        verified_count=verified_count,
        unmapped_keys=mapping.unmapped_keys,
        mismatches=mismatches,
    )


def render_payload_pdf(
    payload: BaseFormInput,
    output_pdf_path: str | Path,
    *,
    allow_unmapped_keys: bool = False,
    payload_path: str | Path | None = None,
    audit_path: str | Path | None = None,
    audit_status: AuditStatus | None = None,
) -> RenderedPdfResult:
    """
    Canonical one-form PDF render path.

    This function owns the deterministic fill flow for a validated payload:
    registered model -> logical filler -> PDF mapping -> PDF write -> read-back verification.
    """

    plan = build_pdf_fill_plan(payload)
    if plan.mapping.unmapped_keys and not allow_unmapped_keys:
        raise ValueError(
            f"PDF mapping incomplete for {payload.form_code}: "
            + ", ".join(plan.mapping.unmapped_keys)
        )
    write_mapped_pdf(plan.blank_pdf_path, output_pdf_path, plan.mapping)
    verification = verify_mapped_pdf(output_pdf_path, plan.mapping)
    if verification.status != "verified":
        raise ValueError(
            f"PDF verification failed for {payload.form_code}: "
            + "; ".join(verification.mismatches)
        )
    return RenderedPdfResult(
        form_code=payload.form_code,
        pdf_filename=plan.pdf_filename,
        output_pdf_path=Path(output_pdf_path),
        verification=verification,
        payload_path=Path(payload_path) if payload_path else None,
        audit_path=Path(audit_path) if audit_path else None,
        audit_status=audit_status,
    )


def discover_case_form_codes(
    case_root: str | Path,
    *,
    tax_year: int = 2025,
) -> list[str]:
    """Discover supported saved payloads under one case input directory."""

    from .registry import FORM_DEFINITIONS

    input_dir = Path(case_root) / "data" / "input" / str(tax_year)
    sample_to_code = {
        definition.sample_json: definition.form_code
        for definition in FORM_DEFINITIONS.values()
    }
    discovered: list[str] = []
    for payload_path in sorted(input_dir.glob("*.json")):
        if payload_path.name.endswith(".audit.json"):
            continue
        form_code = sample_to_code.get(payload_path.name)
        if form_code:
            discovered.append(form_code)
    return discovered


def fill_case_forms(
    case_root: str | Path,
    *,
    tax_year: int = 2025,
    form_codes: list[str] | None = None,
    output_mode: Literal["verified", "draft"] = "verified",
    run_id: str | None = None,
) -> PdfFillRunResult:
    """
    Canonical case-level PDF fill path.

    This helper loads saved payloads and sidecars from the case artifact layout,
    renders each form into a new run directory, verifies each written PDF, and
    writes the run manifest plus verification report.
    """

    from .registry import get_form_definition

    case_root_path = Path(case_root)
    resolved_form_codes = form_codes or discover_case_form_codes(
        case_root_path,
        tax_year=tax_year,
    )
    if not resolved_form_codes:
        raise FileNotFoundError(
            f"No supported form payloads found under {case_root_path / 'data' / 'input' / str(tax_year)}"
        )

    resolved_run_id = run_id or _build_run_id()
    run_dir = case_root_path / "filled-forms" / str(tax_year) / resolved_run_id
    if run_dir.exists():
        raise FileExistsError(f"Fill run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)

    created_at = datetime.now(timezone.utc).isoformat()
    results: list[RenderedPdfResult] = []
    input_paths: dict[str, str] = {}
    output_paths: dict[str, str] = {}
    audit_paths: dict[str, str | None] = {}
    audit_status_by_form: dict[str, AuditStatus | None] = {}
    verification_forms: dict[str, dict[str, object]] = {}

    for form_code in resolved_form_codes:
        definition = get_form_definition(form_code)
        payload_path = case_root_path / "data" / "input" / str(tax_year) / definition.sample_json
        audit_path = payload_path.with_name(f"{payload_path.stem}.audit.json")
        sidecar = _load_audit_sidecar(audit_path)
        input_paths[form_code] = str(payload_path.resolve())
        audit_paths[form_code] = str(audit_path.resolve()) if sidecar else None
        audit_status_by_form[form_code] = sidecar.status if sidecar else None

        try:
            _ensure_fill_mode_allowed(
                form_code,
                sidecar,
                output_mode=output_mode,
            )
            payload = load_payload_for_pdf_fill(payload_path, validation_mode="live")
            output_pdf_path = run_dir / f"{payload_path.stem}.filled.pdf"
            result = render_payload_pdf(
                payload,
                output_pdf_path,
                payload_path=payload_path,
                audit_path=audit_path if sidecar else None,
                audit_status=sidecar.status if sidecar else None,
            )
        except Exception as exc:
            verification_forms[form_code] = {
                "status": "failed",
                "mapped_text_count": 0,
                "mapped_checkbox_count": 0,
                "verified_count": 0,
                "unmapped_keys": [],
                "mismatches": [],
                "error": str(exc),
            }
            manifest_path = _write_fill_manifest(
                run_dir,
                run_id=resolved_run_id,
                tax_year=tax_year,
                requested_forms=resolved_form_codes,
                input_paths=input_paths,
                audit_paths=audit_paths,
                output_paths=output_paths,
                audit_status_by_form=audit_status_by_form,
                created_at=created_at,
                status="failed",
                output_mode=output_mode,
                failure_reason=str(exc),
            )
            verification_report_path = _write_verification_report(
                run_dir,
                run_id=resolved_run_id,
                status="failed",
                forms=verification_forms,
            )
            raise ValueError(
                f"PDF fill run failed for {form_code}: {exc}. "
                f"See {manifest_path} and {verification_report_path}"
            ) from exc

        results.append(result)
        output_paths[form_code] = str(result.output_pdf_path.resolve())
        verification_forms[form_code] = result.verification.to_dict()

    manifest_path = _write_fill_manifest(
        run_dir,
        run_id=resolved_run_id,
        tax_year=tax_year,
        requested_forms=resolved_form_codes,
        input_paths=input_paths,
        audit_paths=audit_paths,
        output_paths=output_paths,
        audit_status_by_form=audit_status_by_form,
        created_at=created_at,
        status=output_mode,
        output_mode=output_mode,
        failure_reason=None,
    )
    verification_report_path = _write_verification_report(
        run_dir,
        run_id=resolved_run_id,
        status=output_mode,
        forms=verification_forms,
    )
    return PdfFillRunResult(
        run_id=resolved_run_id,
        run_dir=run_dir,
        manifest_path=manifest_path,
        verification_report_path=verification_report_path,
        status=output_mode,
        forms=results,
    )


def _read_written_pdf_values(
    pdf_path: str | Path,
) -> tuple[dict[str, str], dict[str, str]]:
    reader = PdfReader(str(pdf_path))
    text_values: dict[str, str] = {}
    checkbox_values: dict[str, str] = {}
    for page in reader.pages:
        annots = page.get("/Annots", [])
        if hasattr(annots, "get_object"):
            annots = annots.get_object()
        for annot_ref in annots:
            annot = annot_ref.get_object()
            field_name = annot.get("/T")
            if not field_name:
                continue
            text_values[field_name] = _pdf_value_to_string(annot.get("/V"))
            checkbox_values[field_name] = _pdf_value_to_string(
                annot.get("/AS") or annot.get("/V")
            )
    return text_values, checkbox_values


def _pdf_value_to_string(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _load_audit_sidecar(audit_path: Path) -> FormAuditSidecar | None:
    if not audit_path.exists():
        return None
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    return FormAuditSidecar.model_validate(payload)


def _ensure_fill_mode_allowed(
    form_code: str,
    sidecar: FormAuditSidecar | None,
    *,
    output_mode: Literal["verified", "draft"],
) -> None:
    if sidecar is None:
        if output_mode == "verified":
            raise ValueError(
                f"Verified PDF fill for {form_code} requires a matching audit sidecar"
            )
        return
    if sidecar.status == "blocked":
        raise ValueError(f"Audit status is blocked for {form_code}")
    if output_mode == "verified" and sidecar.status != "accepted":
        raise ValueError(
            f"Verified PDF fill for {form_code} requires accepted audit status, got {sidecar.status}"
        )


def _build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _write_fill_manifest(
    run_dir: Path,
    *,
    run_id: str,
    tax_year: int,
    requested_forms: list[str],
    input_paths: dict[str, str],
    audit_paths: dict[str, str | None],
    output_paths: dict[str, str],
    audit_status_by_form: dict[str, AuditStatus | None],
    created_at: str,
    status: Literal["verified", "draft", "failed"],
    output_mode: Literal["verified", "draft"],
    failure_reason: str | None,
) -> Path:
    manifest_path = run_dir / "fill-manifest.json"
    payload: dict[str, object] = {
        "run_id": run_id,
        "tax_year": tax_year,
        "status": status,
        "output_mode": output_mode,
        "forms": requested_forms,
        "input_paths": input_paths,
        "audit_paths": audit_paths,
        "output_paths": output_paths,
        "audit_status_by_form": audit_status_by_form,
        "created_at": created_at,
    }
    if failure_reason:
        payload["failure_reason"] = failure_reason
    _write_json_payload(manifest_path, payload)
    return manifest_path


def _write_verification_report(
    run_dir: Path,
    *,
    run_id: str,
    status: Literal["verified", "draft", "failed"],
    forms: dict[str, dict[str, object]],
) -> Path:
    report_path = run_dir / "verification-report.json"
    _write_json_payload(
        report_path,
        {
            "run_id": run_id,
            "status": status,
            "forms": forms,
        },
    )
    return report_path


def _write_json_payload(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
