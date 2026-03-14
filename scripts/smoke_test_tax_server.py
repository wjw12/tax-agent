"""Run a live smoke test against the configured tax-server instance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.tax_server_client import DEFAULT_TAX_SERVER_BASE_URL, TaxServerClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke test the configured tax-server instance.")
    parser.add_argument("--base-url", default=None, help=f"Override base URL (default env or {DEFAULT_TAX_SERVER_BASE_URL}).")
    parser.add_argument("--api-key", default=None, help="Override TAX_SERVER_API_KEY for this run.")
    parser.add_argument(
        "--pdf",
        default=str(ROOT / "2025-empty-forms" / "f1040.pdf"),
        help="PDF to upload to /v1/pdf/process.",
    )
    parser.add_argument("--case-id", default="smoke-test", help="Case ID sent with the upload.")
    parser.add_argument(
        "--use-mistral-fallback",
        action="store_true",
        help="Enable Mistral fallback during PDF processing.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    stage = "health"
    try:
        with TaxServerClient(base_url=args.base_url, api_key=args.api_key) as client:
            resolved_base_url = client.base_url
            health = client.health()
            stage = "auth.inspect"
            inspect = client.inspect_auth()
            stage = "pdf.process"
            processed = client.process_pdf(
                pdf_path,
                case_id=args.case_id,
                use_mistral_fallback=args.use_mistral_fallback,
            )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        print(
            json.dumps(
                {
                    "stage": stage,
                    "base_url": str(exc.request.url).rsplit("/", 3)[0],
                    "status_code": exc.response.status_code,
                    "error": detail or str(exc),
                },
                indent=2,
            )
        )
        return 1

    summary = {
        "base_url": resolved_base_url,
        "pdf": str(pdf_path),
        "health": health,
        "inspect": inspect,
        "process": {
            "job_id": processed["job_id"],
            "filename": processed["filename"],
            "page_count": processed["page_count"],
            "input_uri": processed["input_uri"],
            "result_uri": processed["result_uri"],
            "usage": processed["usage"],
            "features_used": processed["result"]["features_used"],
        },
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
