"""Helpers for validated JSON artifact writes."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
from pathlib import Path
from typing import Any

from .audit_models import FormAuditSidecar
from .registry import FORM_DEFINITIONS, parse_form_input

_LIVE_CASE_INPUT_WRITE_ENABLED: ContextVar[bool] = ContextVar(
    "live_case_input_write_enabled",
    default=False,
)


def _is_live_case_path(path: Path) -> bool:
    return "workspace/cases" in str(path.resolve())


def _is_live_case_input_path(path: Path) -> bool:
    resolved = path.resolve()
    normalized = str(resolved).replace("\\", "/")
    return _is_live_case_path(resolved) and "/data/input/" in normalized


@contextmanager
def _allow_live_case_input_writes():
    token = _LIVE_CASE_INPUT_WRITE_ENABLED.set(True)
    try:
        yield
    finally:
        _LIVE_CASE_INPUT_WRITE_ENABLED.reset(token)


def _ensure_write_allowed(path: Path) -> None:
    if _is_live_case_input_path(path) and not _LIVE_CASE_INPUT_WRITE_ENABLED.get():
        raise ValueError(
            "Direct writes to case input artifacts are not allowed; "
            "use src.live_case_builder.LiveCaseBuilder"
        )


def validate_json_artifact(path: Path, payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    if path.name.endswith(".audit.json"):
        FormAuditSidecar.model_validate(payload)
        return
    form_code = payload.get("form_code")
    if form_code in FORM_DEFINITIONS:
        validation_mode = "live" if _is_live_case_path(path) else "reference"
        parse_form_input(form_code, payload, validation_mode=validation_mode)


def write_json_artifact(path: str | Path, payload: Any) -> None:
    resolved = Path(path)
    _ensure_write_allowed(resolved)
    validate_json_artifact(resolved, payload)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
