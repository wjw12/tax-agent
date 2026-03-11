"""Logical field builders and PDF form fill helpers."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject

from .core import FormComputation, digits_only, format_irs_dollar
from .models import (
    Form1040Input,
    Form1040SRInput,
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
from .processors import (
    process_1040,
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


def _identity_fields(data: Form1040Input | Form1040SRInput) -> dict[str, str]:
    fields = {
        "taxpayer_first_name": data.taxpayer.first_name,
        "taxpayer_last_name": data.taxpayer.last_name,
        "taxpayer_ssn": digits_only(data.taxpayer.ssn),
        "taxpayer_address_line1": data.taxpayer.address.line1,
        "taxpayer_city": data.taxpayer.address.city,
        "taxpayer_state": data.taxpayer.address.state,
        "taxpayer_postal_code": data.taxpayer.address.postal_code,
        "filing_status": data.filing_status,
    }
    if data.spouse:
        fields.update(
            {
                "spouse_first_name": data.spouse.first_name,
                "spouse_last_name": data.spouse.last_name,
                "spouse_ssn": digits_only(data.spouse.ssn),
            }
        )
    return fields


def _full_name(first_name: str, last_name: str) -> str:
    return " ".join(part for part in (first_name, last_name) if part).strip()


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


def write_filled_pdf(
    blank_pdf_path: str | Path,
    output_pdf_path: str | Path,
    field_values: dict[str, str],
    field_map: dict[str, str] | None = None,
) -> Path:
    reader = PdfReader(str(blank_pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    mapped_values = {
        (field_map.get(key, key) if field_map else key): value for key, value in field_values.items()
    }
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
            if field_name not in mapped_values:
                continue
            value = TextStringObject(mapped_values[field_name])
            annot[NameObject("/V")] = value
            annot[NameObject("/DV")] = value
    output_path = Path(output_pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path
