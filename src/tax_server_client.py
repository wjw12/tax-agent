"""Shared client and config for the external tax-server API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx


def load_local_env(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


ROOT_DIR = Path(__file__).resolve().parent.parent
load_local_env(ROOT_DIR / ".env")

DEFAULT_TAX_SERVER_BASE_URL = "http://34.10.4.155:8010"
TAX_SERVER_BASE_URL = os.environ.get("TAX_SERVER_BASE_URL", DEFAULT_TAX_SERVER_BASE_URL).rstrip("/")
TAX_SERVER_API_KEY = os.environ.get("TAX_SERVER_API_KEY", "").strip()
TAX_SERVER_TIMEOUT_SECONDS = float(os.environ.get("TAX_SERVER_TIMEOUT_SECONDS", "120"))
API_KEY_HEADER = "x-api-key"


class TaxServerClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or TAX_SERVER_BASE_URL).rstrip("/")
        self.api_key = (api_key if api_key is not None else TAX_SERVER_API_KEY).strip()
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
            raise ValueError("TAX_SERVER_API_KEY is required for this request.")
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
        case_id: str = "smoke-test",
        use_mistral_fallback: bool = False,
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
