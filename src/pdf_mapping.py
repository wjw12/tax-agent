"""Map logical form values to actual IRS PDF field names."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent
FORMS_DIR = BASE_DIR / "2025-empty-forms"
FIELD_MAP_DIR = Path(__file__).resolve().parent / "field_maps"


LINE_ALIASES: dict[str, dict[str, str]] = {
    "1040": {"1": "1a", "7": "7a", "11": "11a", "12": "12e", "13": "13a"},
    "1040-SR": {
        "1": "1a",
        "7": "7a",
        "11": "11a",
        "12": "12e",
        "13": "13a",
        "28": "29",
    },
    "1040-Schedule-1": {"10": "9", "26": "25"},
    "1040-Schedule-E": {"3": "23a", "20": "31", "21": "32"},
    "2441": {"9": "9a", "13": "14"},
    "4562": {"14": "15", "22": "21"},
    "8829": {"18": "24", "20": "26", "36": "37"},
    "8863": {"4": "11", "30": "18"},
    "8889": {"2": "8", "16": "18"},
    "8995": {"1": "3", "6": "5", "15": "16"},
    "8995-A": {"1": "29", "7": "31", "25": "32", "26": "33"},
}


TEXT_OVERRIDES: dict[str, dict[str, str]] = {
    "1040": {
        "taxpayer_first_name": "f1_14[0]",
        "taxpayer_last_name": "f1_15[0]",
        "taxpayer_ssn": "f1_16[0]",
        "spouse_first_name": "f1_17[0]",
        "spouse_last_name": "f1_18[0]",
        "spouse_ssn": "f1_19[0]",
        "taxpayer_address_line1": "f1_20[0]",
        "taxpayer_city": "f1_22[0]",
        "taxpayer_state": "f1_23[0]",
        "taxpayer_postal_code": "f1_24[0]",
    },
    "1040-SR": {
        "taxpayer_first_name": "f1_14[0]",
        "taxpayer_last_name": "f1_15[0]",
        "taxpayer_ssn": "f1_16[0]",
        "spouse_first_name": "f1_17[0]",
        "spouse_last_name": "f1_18[0]",
        "spouse_ssn": "f1_19[0]",
        "taxpayer_address_line1": "f1_20[0]",
        "taxpayer_city": "f1_22[0]",
        "taxpayer_state": "f1_23[0]",
        "taxpayer_postal_code": "f1_24[0]",
    },
    "8949": {
        "short_term_total": "f1_95[0]",
        "long_term_total": "f2_95[0]",
    },
    "1040-Schedule-EIC": {
        "return_name": "f1_01[0]",
        "return_ssn": "f1_02[0]",
        "child_1_name": "f1_03[0]",
        "child_2_name": "f1_04[0]",
        "child_3_name": "f1_05[0]",
        "child_1_ssn": "f1_06[0]",
        "child_2_ssn": "f1_07[0]",
        "child_3_ssn": "f1_08[0]",
        "child_1_birth_year_digit_1": "f1_09[0]",
        "child_1_birth_year_digit_2": "f1_10[0]",
        "child_1_birth_year_digit_3": "f1_11[0]",
        "child_1_birth_year_digit_4": "f1_12[0]",
        "child_2_birth_year_digit_1": "f1_13[0]",
        "child_2_birth_year_digit_2": "f1_14[0]",
        "child_2_birth_year_digit_3": "f1_15[0]",
        "child_2_birth_year_digit_4": "f1_16[0]",
        "child_3_birth_year_digit_1": "f1_17[0]",
        "child_3_birth_year_digit_2": "f1_18[0]",
        "child_3_birth_year_digit_3": "f1_19[0]",
        "child_3_birth_year_digit_4": "f1_20[0]",
        "child_1_relationship": "f1_21[0]",
        "child_2_relationship": "f1_22[0]",
        "child_3_relationship": "f1_23[0]",
        "child_1_months_lived": "f1_24[0]",
        "child_2_months_lived": "f1_25[0]",
        "child_3_months_lived": "f1_26[0]",
    },
    "8862": {
        "return_name": "f1_01[0]",
        "return_ssn": "f1_02[0]",
        "filing_tax_year": "f1_03[0]",
        "part_ii_child_1_name": "f1_04[0]",
        "part_ii_child_2_name": "f1_05[0]",
        "part_ii_child_3_name": "f1_06[0]",
        "part_ii_child_1_days_lived": "f1_07[0]",
        "part_ii_child_2_days_lived": "f1_08[0]",
        "part_ii_child_3_days_lived": "f1_09[0]",
        "part_ii_child_1_birth_month": "f1_10[0]",
        "part_ii_child_1_birth_day": "f1_11[0]",
        "part_ii_child_1_death_month": "f1_12[0]",
        "part_ii_child_1_death_day": "f1_13[0]",
        "part_ii_child_2_birth_month": "f1_14[0]",
        "part_ii_child_2_birth_day": "f1_15[0]",
        "part_ii_child_2_death_month": "f1_16[0]",
        "part_ii_child_2_death_day": "f1_17[0]",
        "part_ii_child_3_birth_month": "f1_18[0]",
        "part_ii_child_3_birth_day": "f1_19[0]",
        "part_ii_child_3_death_month": "f1_20[0]",
        "part_ii_child_3_death_day": "f1_21[0]",
        "part_ii_section_b_line_9a": "f2_01[0]",
        "part_ii_section_b_line_9b": "f2_02[0]",
        "part_ii_section_b_line_10a": "f2_03[0]",
        "part_ii_section_b_line_10b": "f2_04[0]",
        "part_iii_child_1_name": "f2_05[0]",
        "part_iii_child_2_name": "f2_06[0]",
        "part_iii_child_3_name": "f2_07[0]",
        "part_iii_child_4_name": "f2_08[0]",
        "part_iii_other_dependent_1_name": "f2_09[0]",
        "part_iii_other_dependent_2_name": "f2_10[0]",
        "part_iii_other_dependent_3_name": "f2_11[0]",
        "part_iii_other_dependent_4_name": "f2_12[0]",
        "part_iv_student_1_name": "f3_01[0]",
        "part_iv_student_2_name": "f3_02[0]",
        "part_iv_student_3_name": "f3_03[0]",
    },
}


LINE_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    "1040-Schedule-C": {"31": "f1_46[0]"},
    "1040-Schedule-D": {
        "7": "f1_6[0]",
        "15": "f1_43[0]",
        "16": "f2_1[0]",
        "21": "f2_4[0]",
    },
    "1040-SR": {"15": "f2_24[0]"},
    "1040-Schedule-SE": {
        "2": "f1_5[0]",
        "4c": "f1_9[0]",
        "12": "f1_21[0]",
        "13": "f1_22[0]",
    },
}


CHECKBOX_OVERRIDES: dict[str, dict[str, tuple[str, str]]] = {
    "1040": {
        "filing_status:single": ("c1_8[0]", "/1"),
        "filing_status:married_filing_jointly": ("c1_8[0]", "/2"),
        "filing_status:married_filing_separately": ("c1_8[0]", "/3"),
        "filing_status:head_of_household": ("c1_8[0]", "/4"),
        "filing_status:qualifying_surviving_spouse": ("c1_8[0]", "/5"),
    },
    "1040-SR": {
        "filing_status:single": ("c1_8[0]", "/1"),
        "filing_status:married_filing_jointly": ("c1_8[0]", "/2"),
        "filing_status:married_filing_separately": ("c1_8[0]", "/3"),
        "filing_status:head_of_household": ("c1_8[0]", "/4"),
        "filing_status:qualifying_surviving_spouse": ("c1_8[0]", "/5"),
    },
    "1040-Schedule-EIC": {
        "child_1_student_status:yes": ("c1_1[0]", "/1"),
        "child_1_student_status:no": ("c1_1[0]", "/2"),
        "child_2_student_status:yes": ("c1_2[0]", "/1"),
        "child_2_student_status:no": ("c1_2[0]", "/2"),
        "child_3_student_status:yes": ("c1_3[0]", "/1"),
        "child_3_student_status:no": ("c1_3[0]", "/2"),
        "child_1_disability_status:yes": ("c1_4[0]", "/1"),
        "child_1_disability_status:no": ("c1_4[0]", "/2"),
        "child_2_disability_status:yes": ("c1_5[0]", "/1"),
        "child_2_disability_status:no": ("c1_5[0]", "/2"),
        "child_3_disability_status:yes": ("c1_6[0]", "/1"),
        "child_3_disability_status:no": ("c1_6[0]", "/2"),
    },
    "8862": {
        "claim_eic:yes": ("c1_1[0]", "/1"),
        "claim_ctc_odc:yes": ("c1_2[0]", "/1"),
        "claim_aotc:yes": ("c1_3[0]", "/1"),
        "part_ii_line_3:yes": ("c1_4[0]", "/1"),
        "part_ii_line_3:no": ("c1_4[1]", "/2"),
        "part_ii_line_4:yes": ("c1_5[0]", "/1"),
        "part_ii_line_4:no": ("c1_5[1]", "/2"),
        "part_ii_line_6:yes": ("c1_6[0]", "/1"),
        "part_ii_line_6:no": ("c1_6[1]", "/2"),
        "part_ii_section_b_line_11a:yes": ("c2_1[0]", "/1"),
        "part_ii_section_b_line_11a:no": ("c2_1[1]", "/2"),
        "part_ii_section_b_line_11b:yes": ("c2_2[0]", "/1"),
        "part_ii_section_b_line_11b:no": ("c2_2[1]", "/2"),
        "part_iii_line_14_child_1:yes": ("c2_3[0]", "/1"),
        "part_iii_line_14_child_1:no": ("c2_3[1]", "/2"),
        "part_iii_line_14_child_2:yes": ("c2_4[0]", "/1"),
        "part_iii_line_14_child_2:no": ("c2_4[1]", "/2"),
        "part_iii_line_14_child_3:yes": ("c2_5[0]", "/1"),
        "part_iii_line_14_child_3:no": ("c2_5[1]", "/2"),
        "part_iii_line_14_child_4:yes": ("c2_6[0]", "/1"),
        "part_iii_line_14_child_4:no": ("c2_6[1]", "/2"),
        "part_iii_line_15_child_1:yes": ("c2_7[0]", "/1"),
        "part_iii_line_15_child_1:no": ("c2_7[1]", "/2"),
        "part_iii_line_15_child_2:yes": ("c2_8[0]", "/1"),
        "part_iii_line_15_child_2:no": ("c2_8[1]", "/2"),
        "part_iii_line_15_child_3:yes": ("c2_9[0]", "/1"),
        "part_iii_line_15_child_3:no": ("c2_9[1]", "/2"),
        "part_iii_line_15_child_4:yes": ("c2_10[0]", "/1"),
        "part_iii_line_15_child_4:no": ("c2_10[1]", "/2"),
        "part_iii_line_16_child_1:yes": ("c2_11[0]", "/1"),
        "part_iii_line_16_child_1:no": ("c2_11[1]", "/2"),
        "part_iii_line_16_child_2:yes": ("c2_12[0]", "/1"),
        "part_iii_line_16_child_2:no": ("c2_12[1]", "/2"),
        "part_iii_line_16_child_3:yes": ("c2_13[0]", "/1"),
        "part_iii_line_16_child_3:no": ("c2_13[1]", "/2"),
        "part_iii_line_16_child_4:yes": ("c2_14[0]", "/1"),
        "part_iii_line_16_child_4:no": ("c2_14[1]", "/2"),
        "part_iii_line_16_other_dependent_1:yes": ("c2_15[0]", "/1"),
        "part_iii_line_16_other_dependent_1:no": ("c2_15[1]", "/2"),
        "part_iii_line_16_other_dependent_2:yes": ("c2_16[0]", "/1"),
        "part_iii_line_16_other_dependent_2:no": ("c2_16[1]", "/2"),
        "part_iii_line_16_other_dependent_3:yes": ("c2_17[0]", "/1"),
        "part_iii_line_16_other_dependent_3:no": ("c2_17[1]", "/2"),
        "part_iii_line_16_other_dependent_4:yes": ("c2_18[0]", "/1"),
        "part_iii_line_16_other_dependent_4:no": ("c2_18[1]", "/2"),
        "part_iii_line_17_child_1:yes": ("c2_19[0]", "/1"),
        "part_iii_line_17_child_1:no": ("c2_19[1]", "/2"),
        "part_iii_line_17_child_2:yes": ("c2_20[0]", "/1"),
        "part_iii_line_17_child_2:no": ("c2_20[1]", "/2"),
        "part_iii_line_17_child_3:yes": ("c2_21[0]", "/1"),
        "part_iii_line_17_child_3:no": ("c2_21[1]", "/2"),
        "part_iii_line_17_child_4:yes": ("c2_22[0]", "/1"),
        "part_iii_line_17_child_4:no": ("c2_22[1]", "/2"),
        "part_iii_line_17_other_dependent_1:yes": ("c2_23[0]", "/1"),
        "part_iii_line_17_other_dependent_1:no": ("c2_23[1]", "/2"),
        "part_iii_line_17_other_dependent_2:yes": ("c2_24[0]", "/1"),
        "part_iii_line_17_other_dependent_2:no": ("c2_24[1]", "/2"),
        "part_iii_line_17_other_dependent_3:yes": ("c2_25[0]", "/1"),
        "part_iii_line_17_other_dependent_3:no": ("c2_25[1]", "/2"),
        "part_iii_line_17_other_dependent_4:yes": ("c2_26[0]", "/1"),
        "part_iii_line_17_other_dependent_4:no": ("c2_26[1]", "/2"),
        "part_iv_line_19a_student_1:yes": ("c3_1[0]", "/1"),
        "part_iv_line_19a_student_1:no": ("c3_1[1]", "/2"),
        "part_iv_line_19a_student_2:yes": ("c3_2[0]", "/1"),
        "part_iv_line_19a_student_2:no": ("c3_2[1]", "/2"),
        "part_iv_line_19a_student_3:yes": ("c3_3[0]", "/1"),
        "part_iv_line_19a_student_3:no": ("c3_3[1]", "/2"),
        "part_iv_line_19b_student_1:yes": ("c3_4[0]", "/1"),
        "part_iv_line_19b_student_1:no": ("c3_4[1]", "/2"),
        "part_iv_line_19b_student_2:yes": ("c3_5[0]", "/1"),
        "part_iv_line_19b_student_2:no": ("c3_5[1]", "/2"),
        "part_iv_line_19b_student_3:yes": ("c3_6[0]", "/1"),
        "part_iv_line_19b_student_3:no": ("c3_6[1]", "/2"),
    },
}


@dataclass
class PdfFieldMapping:
    pdf_filename: str
    mapped_text_fields: dict[str, str]
    mapped_checkbox_fields: dict[str, tuple[str, str]]
    unmapped_keys: list[str]
    ignored_keys: list[str]
    line_field_map: dict[str, str]
    available_fields: list[str]


def _to_mm(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"([-0-9.]+)(mm|pt|in)$", value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2)
    if unit == "mm":
        return number
    if unit == "pt":
        return number * 25.4 / 72.0
    if unit == "in":
        return number * 25.4
    return None


def _extract_xfa_template_root(reader: PdfReader) -> ET.Element | None:
    root = reader.trailer["/Root"]
    acroform = root.get("/AcroForm")
    acroform = acroform.get_object() if acroform else None
    if not acroform or "/XFA" not in acroform:
        return None
    xfa = acroform["/XFA"]
    for idx in range(0, len(xfa), 2):
        if str(xfa[idx]) == "template":
            payload = xfa[idx + 1].get_object().get_data()
            return ET.fromstring(payload)
    return None


def _is_text_field(element: ET.Element) -> bool:
    for child in element.iter():
        tag = child.tag.split("}")[-1]
        if tag in {"checkButton", "choiceList"}:
            return False
        if tag == "textEdit":
            return True
    return False


def extract_line_field_map(pdf_path: str | Path) -> dict[str, str]:
    reader = PdfReader(str(pdf_path))
    root = _extract_xfa_template_root(reader)
    if root is None:
        return {}

    fields: list[tuple[str, float, float]] = []
    labels: list[tuple[str, float, float]] = []
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        name = element.attrib.get("name")
        x = _to_mm(element.attrib.get("x"))
        y = _to_mm(element.attrib.get("y"))
        if tag == "field" and name and x is not None and y is not None and _is_text_field(element):
            fields.append((name, x, y))
        elif tag == "draw" and name and name.startswith("Ln") and x is not None and y is not None:
            labels.append((name, x, y))

    mapping: dict[str, str] = {}
    for label_name, label_x, label_y in labels:
        candidates: list[tuple[float, float, str]] = []
        for field_name, field_x, field_y in fields:
            if abs(field_y - label_y) > 3.6:
                continue
            if field_x + 0.1 < label_x:
                continue
            candidates.append((field_x - label_x, abs(field_y - label_y), field_name))
        if not candidates:
            continue
        candidates.sort(key=lambda item: (item[1], item[0]))
        mapping[label_name] = f"{candidates[0][2]}[0]"
    return mapping


def _line_to_label(form_code: str, line_id: str) -> str | None:
    mapped = LINE_ALIASES.get(form_code, {}).get(line_id, line_id)
    normalized = mapped.strip()
    if not re.fullmatch(r"[0-9]+[A-Za-z]?", normalized):
        return None
    return f"Ln{normalized.lower()}"


def build_pdf_field_mapping(form_code: str, pdf_filename: str, logical_fields: dict[str, str]) -> PdfFieldMapping:
    pdf_path = FORMS_DIR / pdf_filename
    reader = PdfReader(str(pdf_path))
    available_fields = sorted((reader.get_fields() or {}).keys())
    line_field_map = extract_line_field_map(pdf_path)
    mapped_text_fields: dict[str, str] = {}
    mapped_checkbox_fields: dict[str, tuple[str, str]] = {}
    unmapped_keys: list[str] = []
    ignored_keys: list[str] = []

    manual_text = TEXT_OVERRIDES.get(form_code, {})
    manual_checkboxes = CHECKBOX_OVERRIDES.get(form_code, {})

    for logical_key, value in logical_fields.items():
        if logical_key in manual_text:
            mapped_text_fields[manual_text[logical_key]] = value
            continue
        checkbox = manual_checkboxes.get(f"{logical_key}:{value}")
        if checkbox:
            mapped_checkbox_fields[checkbox[0]] = checkbox
            continue
        if logical_key == "filing_status":
            checkbox = manual_checkboxes.get(f"filing_status:{value}")
            if checkbox:
                mapped_checkbox_fields[checkbox[0]] = checkbox
            else:
                unmapped_keys.append(logical_key)
            continue
        if logical_key.startswith("line_"):
            line_id = logical_key.removeprefix("line_")
            line_override = LINE_FIELD_OVERRIDES.get(form_code, {}).get(line_id)
            if line_override:
                mapped_text_fields[line_override] = value
                continue
            label = _line_to_label(form_code, line_id)
            if not label:
                unmapped_keys.append(logical_key)
                continue
            pdf_field = line_field_map.get(label)
            if pdf_field:
                mapped_text_fields[pdf_field] = value
            else:
                unmapped_keys.append(logical_key)
            continue
        if logical_key.startswith("meta_"):
            ignored_keys.append(logical_key)
            continue
        unmapped_keys.append(logical_key)

    return PdfFieldMapping(
        pdf_filename=pdf_filename,
        mapped_text_fields=mapped_text_fields,
        mapped_checkbox_fields=mapped_checkbox_fields,
        unmapped_keys=sorted(set(unmapped_keys)),
        ignored_keys=sorted(set(ignored_keys)),
        line_field_map=line_field_map,
        available_fields=available_fields,
    )


def write_field_map_snapshot(form_code: str, mapping: PdfFieldMapping) -> Path:
    FIELD_MAP_DIR.mkdir(parents=True, exist_ok=True)
    output_path = FIELD_MAP_DIR / f"{form_code.lower().replace('/', '_')}.json"
    payload = {
        "pdf_filename": mapping.pdf_filename,
        "mapped_text_fields": mapping.mapped_text_fields,
        "mapped_checkbox_fields": {
            key: {"field": field_name, "on_value": on_value}
            for key, (field_name, on_value) in mapping.mapped_checkbox_fields.items()
        },
        "unmapped_keys": mapping.unmapped_keys,
        "ignored_keys": mapping.ignored_keys,
        "line_field_map": mapping.line_field_map,
        "available_fields": mapping.available_fields,
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path
