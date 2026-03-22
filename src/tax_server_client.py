"""Shared client and config for the external tax-server API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


TAX_SERVER_BASE_URL = "https://tax.heurist.xyz"
TAX_SERVER_TIMEOUT_SECONDS = 120.0
API_KEY_HEADER = "x-api-key"


class TaxServerClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = TAX_SERVER_BASE_URL
        self.api_key = (api_key if api_key is not None else "").strip()
        self.timeout_seconds = timeout_seconds or TAX_SERVER_TIMEOUT_SECONDS
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TaxServerClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _headers(self, *, require_api_key: bool) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers[API_KEY_HEADER] = self.api_key
        elif require_api_key:
            raise ValueError("A tax-server API key is required. Pass --api-key on the CLI.")
        return headers

    def health(self) -> dict[str, Any]:
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()

    def inspect_auth(self) -> dict[str, Any]:
        response = self._client.post("/v1/auth/inspect", headers=self._headers(require_api_key=True))
        response.raise_for_status()
        return response.json()

    def process_pdf(
        self,
        pdf_path: str | Path,
        *,
        case_id: str = "pdf-process",
        use_mistral_fallback: bool = True,
    ) -> dict[str, Any]:
        upload_path = Path(pdf_path)
        with upload_path.open("rb") as handle:
            response = self._client.post(
                "/v1/pdf/process",
                headers=self._headers(require_api_key=True),
                data={
                    "case_id": case_id,
                    "use_mistral_fallback": str(use_mistral_fallback).lower(),
                },
                files={
                    "file": (upload_path.name, handle, "application/pdf"),
                },
            )
        response.raise_for_status()
        return response.json()
