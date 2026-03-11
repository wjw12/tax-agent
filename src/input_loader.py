"""Load sample JSON inputs and audit sidecars from disk."""

from __future__ import annotations

import json
from pathlib import Path

from .audit_models import FormAuditSidecar
from .models import BaseFormInput
from .registry import FORM_DEFINITIONS, parse_form_input


DEFAULT_INPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "input" / "2025"


def load_form_input(path: str | Path) -> BaseFormInput:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    form_code = payload["form_code"]
    return parse_form_input(form_code, payload)


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
