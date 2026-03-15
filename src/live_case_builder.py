"""Canonical writer for live case payloads and audit sidecars."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .audit_models import (
    AuditIssue,
    AuditSourceEntry,
    AuditStatus,
    ComputationTrace,
    FormAuditSidecar,
    RuntimeExtractionResult,
)
from .case_artifacts import _allow_live_case_input_writes, write_json_artifact
from .registry import get_form_definition


@dataclass(frozen=True)
class LiveCaseWriteResult:
    form_code: str
    payload_path: Path
    audit_path: Path


def _to_input_dir(case_root: str | Path, tax_year: int) -> Path:
    return Path(case_root) / "data" / "input" / str(tax_year)


def _to_sidecar_path(payload_path: Path) -> Path:
    return payload_path.with_name(f"{payload_path.stem}.audit.json")


def _normalize_sidecar(
    sidecar: FormAuditSidecar | dict[str, Any],
    *,
    form_code: str,
    tax_year: int,
    payload_path: Path,
) -> dict[str, Any]:
    if isinstance(sidecar, FormAuditSidecar):
        payload = sidecar.model_dump(mode="json", exclude_none=True)
    else:
        payload = dict(sidecar)
    payload.setdefault("form_code", form_code)
    payload.setdefault("tax_year", tax_year)
    payload.setdefault("form_path", str(payload_path))
    validated = FormAuditSidecar.model_validate(payload)
    if validated.form_code != form_code:
        raise ValueError(
            f"Audit sidecar form_code {validated.form_code!r} does not match payload form_code {form_code!r}"
        )
    if validated.tax_year != tax_year:
        raise ValueError(
            f"Audit sidecar tax_year {validated.tax_year} does not match payload tax_year {tax_year}"
        )
    return validated.model_dump(mode="json", exclude_none=True)


def _normalize_runtime_result(
    result: RuntimeExtractionResult | dict[str, Any],
) -> RuntimeExtractionResult:
    if isinstance(result, RuntimeExtractionResult):
        return result
    return RuntimeExtractionResult.model_validate(result)


class LiveCaseBuilder:
    """Write validated live-case form artifacts into a case input directory."""

    def __init__(self, case_root: str | Path, *, tax_year: int = 2025) -> None:
        self.case_root = Path(case_root)
        self.tax_year = tax_year
        self.input_dir = _to_input_dir(self.case_root, tax_year)

    def _payload_path_for_form(self, form_code: str) -> Path:
        definition = get_form_definition(form_code)
        return self.input_dir / definition.sample_json

    def _audit_path_for_form(self, form_code: str) -> Path:
        return _to_sidecar_path(self._payload_path_for_form(form_code))

    def _load_existing_sidecar(self, form_code: str) -> FormAuditSidecar:
        audit_path = self._audit_path_for_form(form_code)
        if not audit_path.exists():
            raise FileNotFoundError(f"No existing audit sidecar for {form_code} at {audit_path}")
        return FormAuditSidecar.model_validate(json.loads(audit_path.read_text(encoding="utf-8")))

    def write_form_bundle(
        self,
        payload: dict[str, Any],
        audit_sidecar: FormAuditSidecar | dict[str, Any],
    ) -> LiveCaseWriteResult:
        form_code = payload["form_code"]
        payload_tax_year = int(payload["tax_year"])
        if payload_tax_year != self.tax_year:
            raise ValueError(
                f"Payload tax_year {payload_tax_year} does not match builder tax_year {self.tax_year}"
            )
        payload_path = self._payload_path_for_form(form_code)
        audit_path = _to_sidecar_path(payload_path)
        normalized_sidecar = _normalize_sidecar(
            audit_sidecar,
            form_code=form_code,
            tax_year=self.tax_year,
            payload_path=payload_path,
        )
        with _allow_live_case_input_writes():
            write_json_artifact(payload_path, payload)
            write_json_artifact(audit_path, normalized_sidecar)
        return LiveCaseWriteResult(
            form_code=form_code,
            payload_path=payload_path,
            audit_path=audit_path,
        )

    def write_runtime_result(
        self,
        result: RuntimeExtractionResult | dict[str, Any],
    ) -> LiveCaseWriteResult:
        runtime_result = _normalize_runtime_result(result)
        payload = runtime_result.form_payload
        sidecar_payload = runtime_result.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"form_payload"},
        )
        return self.write_form_bundle(payload, sidecar_payload)

    def write_form(
        self,
        payload: dict[str, Any],
        *,
        status: AuditStatus,
        sources: list[AuditSourceEntry | dict[str, Any]] | None = None,
        computations: list[ComputationTrace | dict[str, Any]] | None = None,
        issues: list[AuditIssue | dict[str, Any]] | None = None,
        form_path: str | None = None,
    ) -> LiveCaseWriteResult:
        form_code = payload["form_code"]
        payload_path = self._payload_path_for_form(form_code)
        sidecar = FormAuditSidecar(
            form_code=form_code,
            tax_year=self.tax_year,
            status=status,
            sources=[
                entry if isinstance(entry, AuditSourceEntry) else AuditSourceEntry.model_validate(entry)
                for entry in (sources or [])
            ],
            computations=[
                entry if isinstance(entry, ComputationTrace) else ComputationTrace.model_validate(entry)
                for entry in (computations or [])
            ],
            issues=[
                entry if isinstance(entry, AuditIssue) else AuditIssue.model_validate(entry)
                for entry in (issues or [])
            ],
            form_path=form_path or str(payload_path),
        )
        return self.write_form_bundle(payload, sidecar)

    def update_audit_sidecar(
        self,
        form_code: str,
        *,
        status: AuditStatus | None = None,
        sources: list[AuditSourceEntry | dict[str, Any]] | None = None,
        computations: list[ComputationTrace | dict[str, Any]] | None = None,
        issues: list[AuditIssue | dict[str, Any]] | None = None,
    ) -> LiveCaseWriteResult:
        payload_path = self._payload_path_for_form(form_code)
        if not payload_path.exists():
            raise FileNotFoundError(f"No existing payload for {form_code} at {payload_path}")

        existing = self._load_existing_sidecar(form_code)
        updated = FormAuditSidecar(
            schema_version=existing.schema_version,
            form_code=existing.form_code,
            tax_year=existing.tax_year,
            status=status or existing.status,
            sources=[
                entry if isinstance(entry, AuditSourceEntry) else AuditSourceEntry.model_validate(entry)
                for entry in (sources if sources is not None else existing.sources)
            ],
            computations=[
                entry if isinstance(entry, ComputationTrace) else ComputationTrace.model_validate(entry)
                for entry in (computations if computations is not None else existing.computations)
            ],
            issues=[
                entry if isinstance(entry, AuditIssue) else AuditIssue.model_validate(entry)
                for entry in (issues if issues is not None else existing.issues)
            ],
            form_path=existing.form_path or str(payload_path),
        )
        with _allow_live_case_input_writes():
            write_json_artifact(self._audit_path_for_form(form_code), updated.model_dump(mode="json", exclude_none=True))
        return LiveCaseWriteResult(
            form_code=form_code,
            payload_path=payload_path,
            audit_path=self._audit_path_for_form(form_code),
        )


def write_live_case_form(
    case_root: str | Path,
    payload: dict[str, Any],
    *,
    status: AuditStatus,
    tax_year: int = 2025,
    sources: list[AuditSourceEntry | dict[str, Any]] | None = None,
    computations: list[ComputationTrace | dict[str, Any]] | None = None,
    issues: list[AuditIssue | dict[str, Any]] | None = None,
    form_path: str | None = None,
) -> LiveCaseWriteResult:
    builder = LiveCaseBuilder(case_root, tax_year=tax_year)
    return builder.write_form(
        payload,
        status=status,
        sources=sources,
        computations=computations,
        issues=issues,
        form_path=form_path,
    )


def write_live_case_runtime_result(
    case_root: str | Path,
    result: RuntimeExtractionResult | dict[str, Any],
    *,
    tax_year: int = 2025,
) -> LiveCaseWriteResult:
    builder = LiveCaseBuilder(case_root, tax_year=tax_year)
    return builder.write_runtime_result(result)
