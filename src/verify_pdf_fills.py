"""Fill every supported sample IRS PDF and verify written values round-trip."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import NameObject

from .input_loader import load_all_sample_inputs
from .pdf_fillers import write_filled_pdf
from .pdf_mapping import BASE_DIR, build_pdf_field_mapping, write_field_map_snapshot
from .registry import FORM_DEFINITIONS, build_field_values


OUTPUT_DIR = BASE_DIR / "workspace" / "verified-filled-forms"


def _set_checkbox_values(pdf_path: Path, checkbox_fields: dict[str, tuple[str, str]]) -> None:
    if not checkbox_fields:
        return
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for field_name, (_, on_value) in checkbox_fields.items():
        for page in writer.pages:
            annots = page.get("/Annots", [])
            if hasattr(annots, "get_object"):
                annots = annots.get_object()
            for annot_ref in annots:
                annot = annot_ref.get_object()
                if annot.get("/T") != field_name:
                    continue
                state = NameObject(on_value)
                annot[NameObject("/V")] = state
                appearance = annot.get("/AP")
                normal_appearances = appearance.get("/N", {}) if appearance else {}
                if on_value in normal_appearances:
                    annot[NameObject("/AS")] = state
                else:
                    annot[NameObject("/AS")] = NameObject("/Off")
    with pdf_path.open("wb") as handle:
        writer.write(handle)


def _read_field_value(reader: PdfReader, field_name: str) -> str | None:
    for page in reader.pages:
        annots = page.get("/Annots", [])
        if hasattr(annots, "get_object"):
            annots = annots.get_object()
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if annot.get("/T") != field_name:
                continue
            raw = annot.get("/V")
            return "" if raw is None else str(raw)
    return None


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_inputs = load_all_sample_inputs()
    report: dict[str, dict[str, object]] = {}
    failures = 0

    for form_code, payload in sample_inputs.items():
        definition = FORM_DEFINITIONS[form_code]
        logical_fields = build_field_values(payload)
        mapping = build_pdf_field_mapping(form_code, definition.pdf_filename, logical_fields)
        write_field_map_snapshot(form_code, mapping)

        blank_pdf = BASE_DIR / "2025-empty-forms" / definition.pdf_filename
        output_pdf = OUTPUT_DIR / f"{form_code.lower().replace('/', '_')}.filled.pdf"
        write_filled_pdf(blank_pdf, output_pdf, mapping.mapped_text_fields)
        _set_checkbox_values(output_pdf, mapping.mapped_checkbox_fields)

        reader = PdfReader(str(output_pdf))
        mismatches: list[dict[str, str]] = []
        for field_name, expected_value in mapping.mapped_text_fields.items():
            actual_value = _read_field_value(reader, field_name)
            if actual_value != expected_value:
                mismatches.append(
                    {
                        "field": field_name,
                        "expected": expected_value,
                        "actual": "<missing>" if actual_value is None else actual_value,
                    }
                )
        for field_name, (_, on_value) in mapping.mapped_checkbox_fields.items():
            actual_value = _read_field_value(reader, field_name)
            if actual_value != on_value:
                mismatches.append(
                    {
                        "field": field_name,
                        "expected": on_value,
                        "actual": "<missing>" if actual_value is None else actual_value,
                    }
                )

        status = "ok"
        if mapping.unmapped_keys or mismatches:
            status = "failed"
            failures += 1

        report[form_code] = {
            "pdf_filename": definition.pdf_filename,
            "mapped_text_count": len(mapping.mapped_text_fields),
            "mapped_checkbox_count": len(mapping.mapped_checkbox_fields),
            "ignored_key_count": len(mapping.ignored_keys),
            "unmapped_keys": mapping.unmapped_keys,
            "mismatches": mismatches,
            "status": status,
        }

    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
