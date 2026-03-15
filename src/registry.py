"""Registry of supported forms, model classes, processors, and fillers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .core import FormComputation
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
from .pdf_fillers import (
    fill_1040_fields,
    fill_1040_nr_schedule_a_fields,
    fill_1040_nr_schedule_nec_fields,
    fill_1040_nr_schedule_oi_fields,
    fill_1040_nr_fields,
    fill_1040_sr_fields,
    fill_2441_fields,
    fill_4562_fields,
    fill_8812_fields,
    fill_8829_fields,
    fill_8862_fields,
    fill_8863_fields,
    fill_8889_fields,
    fill_8949_fields,
    fill_8962_fields,
    fill_8995_a_fields,
    fill_8995_fields,
    fill_schedule_1_a_fields,
    fill_schedule_1_fields,
    fill_schedule_2_fields,
    fill_schedule_3_fields,
    fill_schedule_a_fields,
    fill_schedule_b_fields,
    fill_schedule_c_fields,
    fill_schedule_d_fields,
    fill_schedule_e_fields,
    fill_schedule_eic_fields,
    fill_schedule_se_fields,
)
from .processors import (
    process_1040,
    process_1040_nr_schedule_a,
    process_1040_nr_schedule_nec,
    process_1040_nr_schedule_oi,
    process_1040_nr,
    process_1040_sr,
    process_2441,
    process_4562,
    process_8812,
    process_8829,
    process_8862,
    process_8863,
    process_8889,
    process_8949,
    process_8962,
    process_8995,
    process_8995_a,
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


@dataclass(frozen=True)
class FormDefinition:
    form_code: str
    form_name: str
    pdf_filename: str
    sample_json: str
    model: type[BaseModel]
    processor: Any
    filler: Any


FORM_DEFINITIONS: dict[str, FormDefinition] = {
    "1040": FormDefinition("1040", "Form 1040", "f1040.pdf", "1040.json", Form1040Input, process_1040, fill_1040_fields),
    "1040-NR": FormDefinition("1040-NR", "Form 1040-NR", "f1040nr.pdf", "1040-nr.json", Form1040NRInput, process_1040_nr, fill_1040_nr_fields),
    "1040-NR-Schedule-OI": FormDefinition(
        "1040-NR-Schedule-OI",
        "Schedule OI (Form 1040-NR)",
        "f1040nro.pdf",
        "1040-nr-schedule-oi.json",
        Form1040NRScheduleOIInput,
        process_1040_nr_schedule_oi,
        fill_1040_nr_schedule_oi_fields,
    ),
    "1040-NR-Schedule-A": FormDefinition(
        "1040-NR-Schedule-A",
        "Schedule A (Form 1040-NR)",
        "f1040nra.pdf",
        "1040-nr-schedule-a.json",
        Form1040NRScheduleAInput,
        process_1040_nr_schedule_a,
        fill_1040_nr_schedule_a_fields,
    ),
    "1040-NR-Schedule-NEC": FormDefinition(
        "1040-NR-Schedule-NEC",
        "Schedule NEC (Form 1040-NR)",
        "f1040nrn.pdf",
        "1040-nr-schedule-nec.json",
        Form1040NRScheduleNECInput,
        process_1040_nr_schedule_nec,
        fill_1040_nr_schedule_nec_fields,
    ),
    "1040-SR": FormDefinition("1040-SR", "Form 1040-SR", "f1040s.pdf", "1040-sr.json", Form1040SRInput, process_1040_sr, fill_1040_sr_fields),
    "1040-Schedule-1": FormDefinition("1040-Schedule-1", "Schedule 1 (Form 1040)", "f1040s1.pdf", "1040-schedule-1.json", Schedule1Input, process_schedule_1, fill_schedule_1_fields),
    "1040-Schedule-1-A": FormDefinition(
        "1040-Schedule-1-A",
        "Schedule 1-A (Form 1040)",
        "f1040s1a.pdf",
        "1040-schedule-1-a.json",
        Schedule1AInput,
        process_schedule_1_a,
        fill_schedule_1_a_fields,
    ),
    "1040-Schedule-2": FormDefinition("1040-Schedule-2", "Schedule 2 (Form 1040)", "f1040s2.pdf", "1040-schedule-2.json", Schedule2Input, process_schedule_2, fill_schedule_2_fields),
    "1040-Schedule-3": FormDefinition("1040-Schedule-3", "Schedule 3 (Form 1040)", "f1040s3.pdf", "1040-schedule-3.json", Schedule3Input, process_schedule_3, fill_schedule_3_fields),
    "1040-Schedule-A": FormDefinition("1040-Schedule-A", "Schedule A (Form 1040)", "f1040sa.pdf", "1040-schedule-a.json", ScheduleAInput, process_schedule_a, fill_schedule_a_fields),
    "1040-Schedule-B": FormDefinition("1040-Schedule-B", "Schedule B (Form 1040)", "f1040sb.pdf", "1040-schedule-b.json", ScheduleBInput, process_schedule_b, fill_schedule_b_fields),
    "1040-Schedule-D": FormDefinition("1040-Schedule-D", "Schedule D (Form 1040)", "f1040sd.pdf", "1040-schedule-d.json", ScheduleDInput, process_schedule_d, fill_schedule_d_fields),
    "8949": FormDefinition("8949", "Form 8949", "f8949.pdf", "8949.json", Form8949Input, process_8949, fill_8949_fields),
    "1040-Schedule-C": FormDefinition("1040-Schedule-C", "Schedule C (Form 1040)", "f1040sc.pdf", "1040-schedule-c.json", ScheduleCInput, process_schedule_c, fill_schedule_c_fields),
    "1040-Schedule-SE": FormDefinition("1040-Schedule-SE", "Schedule SE (Form 1040)", "f1040sse.pdf", "1040-schedule-se.json", ScheduleSEInput, process_schedule_se, fill_schedule_se_fields),
    "4562": FormDefinition("4562", "Form 4562", "f4562.pdf", "4562.json", Form4562Input, process_4562, fill_4562_fields),
    "8829": FormDefinition("8829", "Form 8829", "f8829.pdf", "8829.json", Form8829Input, process_8829, fill_8829_fields),
    "8995": FormDefinition("8995", "Form 8995", "f8995.pdf", "8995.json", Form8995Input, process_8995, fill_8995_fields),
    "8995-A": FormDefinition("8995-A", "Form 8995-A", "f8995a.pdf", "8995-a.json", Form8995AInput, process_8995_a, fill_8995_a_fields),
    "1040-Schedule-E": FormDefinition("1040-Schedule-E", "Schedule E (Form 1040)", "f1040se.pdf", "1040-schedule-e.json", ScheduleEInput, process_schedule_e, fill_schedule_e_fields),
    "1040-Schedule-8812": FormDefinition("1040-Schedule-8812", "Schedule 8812 (Form 1040)", "f1040s8.pdf", "1040-schedule-8812.json", Schedule8812Input, process_8812, fill_8812_fields),
    "1040-Schedule-EIC": FormDefinition("1040-Schedule-EIC", "Schedule EIC (Form 1040)", "f1040sei.pdf", "1040-schedule-eic.json", ScheduleEICInput, process_schedule_eic, fill_schedule_eic_fields),
    "2441": FormDefinition("2441", "Form 2441", "f2441.pdf", "2441.json", Form2441Input, process_2441, fill_2441_fields),
    "8863": FormDefinition("8863", "Form 8863", "f8863.pdf", "8863.json", Form8863Input, process_8863, fill_8863_fields),
    "8889": FormDefinition("8889", "Form 8889", "f8889.pdf", "8889.json", Form8889Input, process_8889, fill_8889_fields),
    "8962": FormDefinition("8962", "Form 8962", "f8962.pdf", "8962.json", Form8962Input, process_8962, fill_8962_fields),
    "8862": FormDefinition("8862", "Form 8862", "f8862.pdf", "8862.json", Form8862Input, process_8862, fill_8862_fields),
}


def get_form_definition(form_code: str) -> FormDefinition:
    return FORM_DEFINITIONS[form_code]


def _validate_live_payload_contract(form_code: str, payload: dict[str, Any]) -> None:
    definition = get_form_definition(form_code)
    expected_fields = set(definition.model.model_fields)
    present_fields = set(payload)
    missing_fields = sorted(expected_fields - present_fields)
    if missing_fields:
        raise ValueError(
            "Live payload is missing required top-level fields for "
            f"{form_code}: {', '.join(missing_fields)}"
        )


def parse_form_input(
    form_code: str,
    payload: dict[str, Any],
    *,
    validation_mode: Literal["reference", "live"] = "live",
) -> BaseFormInput:
    definition = get_form_definition(form_code)
    if validation_mode == "live":
        _validate_live_payload_contract(form_code, payload)
    return definition.model.model_validate(payload)


def compute_form(payload: BaseFormInput) -> FormComputation:
    definition = get_form_definition(payload.form_code)
    return definition.processor(payload)


def build_field_values(payload: BaseFormInput) -> dict[str, str]:
    definition = get_form_definition(payload.form_code)
    return definition.filler(payload)


def validate_manifest_coverage(manifest_path: str | Path) -> dict[str, list[str]]:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    missing_models: list[str] = []
    missing_samples: list[str] = []
    missing_fillers: list[str] = []
    for download in payload.get("downloads", []):
        form_code = download["form_code"]
        definition = FORM_DEFINITIONS.get(form_code)
        if definition is None:
            missing_models.append(form_code)
            missing_fillers.append(form_code)
            missing_samples.append(form_code)
            continue
        if not definition.sample_json:
            missing_samples.append(form_code)
        if not definition.filler:
            missing_fillers.append(form_code)
        if not definition.model:
            missing_models.append(form_code)
    return {
        "missing_models": missing_models,
        "missing_fillers": missing_fillers,
        "missing_samples": missing_samples,
    }
