"""Load reference or live JSON inputs and audit sidecars from disk."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from .audit_models import FormAuditSidecar
from .models import BaseFormInput, Form8995AInput, Form8995Input, ScheduleCInput, ScheduleSEInput
from .qbi import build_qbi_business_assembly_from_forms, validate_qbi_form_input_2025
from .registry import FORM_DEFINITIONS, compute_form, parse_form_input


DEFAULT_INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "input" / "2025"


def _is_live_case_path(path: Path) -> bool:
    return "workspace/cases" in str(path.resolve())


def _load_parsed_form(path: Path, *, validation_mode: str) -> BaseFormInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return parse_form_input(payload["form_code"], payload, validation_mode=validation_mode)


def _validate_live_qbi_payload(path: Path, payload: BaseFormInput) -> None:
    if payload.form_code not in {"8995", "8995-A"}:
        return

    tax_year_dir = path.parent
    validation_mode = "live"
    base_return_path = tax_year_dir / FORM_DEFINITIONS["1040"].sample_json
    agi_line = "11"
    if not base_return_path.exists():
        base_return_path = tax_year_dir / FORM_DEFINITIONS["1040-NR"].sample_json
        agi_line = "11b"
    if not base_return_path.exists():
        return

    base_return = _load_parsed_form(base_return_path, validation_mode=validation_mode)
    base_return_result = compute_form(base_return)
    agi = base_return_result.get_line(agi_line)

    schedule_d_path = tax_year_dir / FORM_DEFINITIONS["1040-Schedule-D"].sample_json
    net_capital_gains = Decimal("0")
    if schedule_d_path.exists():
        schedule_d = _load_parsed_form(schedule_d_path, validation_mode=validation_mode)
        net_capital_gains = compute_form(schedule_d).get_line("16")

    business_sources = None
    schedule_c_path = tax_year_dir / FORM_DEFINITIONS["1040-Schedule-C"].sample_json
    if schedule_c_path.exists():
        schedule_c = _load_parsed_form(schedule_c_path, validation_mode=validation_mode)
        if isinstance(schedule_c, ScheduleCInput):
            schedule_se = None
            schedule_se_path = tax_year_dir / FORM_DEFINITIONS["1040-Schedule-SE"].sample_json
            if schedule_se_path.exists():
                loaded_schedule_se = _load_parsed_form(schedule_se_path, validation_mode=validation_mode)
                if isinstance(loaded_schedule_se, ScheduleSEInput):
                    schedule_se = loaded_schedule_se
            business_sources = [
                build_qbi_business_assembly_from_forms(
                    schedule_c,
                    schedule_se,
                )
            ]

    issues = validate_qbi_form_input_2025(
        payload,
        filing_status=base_return.filing_status,
        agi=agi,
        standard_deduction=base_return.standard_deduction,
        itemized_deductions=base_return.itemized_deductions,
        net_capital_gains=net_capital_gains,
        businesses=business_sources,
    )
    if issues:
        bullet_list = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"Live QBI payload failed validation for {path}:\n{bullet_list}")


def load_form_input(path: str | Path) -> BaseFormInput:
    resolved = Path(path).resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    form_code = payload["form_code"]
    validation_mode = "live" if _is_live_case_path(resolved) else "reference"
    parsed = parse_form_input(form_code, payload, validation_mode=validation_mode)
    if validation_mode == "live" and isinstance(parsed, (Form8995Input, Form8995AInput)):
        _validate_live_qbi_payload(resolved, parsed)
    return parsed


def load_form_audit_sidecar(path: str | Path) -> FormAuditSidecar:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return FormAuditSidecar.model_validate(payload)


def load_all_sample_inputs(input_dir: str | Path = DEFAULT_INPUT_DIR) -> dict[str, BaseFormInput]:
    root = Path(input_dir)
    loaded: dict[str, BaseFormInput] = {}
    for form_code, definition in FORM_DEFINITIONS.items():
        payload = load_form_input(root / definition.sample_json)
        loaded[form_code] = payload
    return loaded
