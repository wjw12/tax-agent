"""Load reference or live JSON inputs and audit sidecars from disk."""

from __future__ import annotations

import json
from pathlib import Path

from .audit_models import FormAuditSidecar
from .models import BaseFormInput
from .registry import FORM_DEFINITIONS, parse_form_input


DEFAULT_INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "input" / "2025"


def _is_live_case_path(path: Path) -> bool:
    return "workspace/cases" in str(path.resolve())


def load_form_input(path: str | Path) -> BaseFormInput:
    resolved = Path(path).resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    form_code = payload["form_code"]
    validation_mode = "live" if _is_live_case_path(resolved) else "reference"
    return parse_form_input(form_code, payload, validation_mode=validation_mode)


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
