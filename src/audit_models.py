"""Typed models for minimal evidence-bearing audit sidecars."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AuditStatus = Literal["accepted", "needs_review", "blocked"]
RouterConfidence = Literal["high", "medium", "low"]
IssueSeverity = Literal["info", "low", "medium", "high"]
ScalarValue = str | bool | int


class AuditSourceEntry(BaseModel):
    output_key: str
    value: ScalarValue | None = None
    file: str
    page: int
    locator: str | None = None
    extractor: str | list[str] | None = None
    router_confidence: RouterConfidence | None = None


class ComputationTrace(BaseModel):
    output_key: str
    inputs: list[str] = Field(default_factory=list)
    python_expression: str
    result: ScalarValue


class AuditIssue(BaseModel):
    code: str
    severity: IssueSeverity
    message: str
    related_keys: list[str] = Field(default_factory=list)


class FormAuditSidecar(BaseModel):
    schema_version: str = "1.0"
    form_code: str
    tax_year: int = 2025
    status: AuditStatus
    sources: list[AuditSourceEntry] = Field(default_factory=list)
    computations: list[ComputationTrace] = Field(default_factory=list)
    issues: list[AuditIssue] = Field(default_factory=list)
    form_path: str | None = None


class RuntimeExtractionResult(FormAuditSidecar):
    form_payload: dict[str, Any]
