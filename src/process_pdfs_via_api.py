"""Batch PDF processing via the shared tax-server API."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .case_artifacts import write_json_artifact
from .tax_server_client import TAX_SERVER_BASE_URL, TaxServerClient


def list_pdf_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.glob("*.pdf") if path.is_file())


def resolve_input_paths(input_dir: Path, files: list[str]) -> list[Path]:
    if not files:
        return list_pdf_files(input_dir)

    resolved: list[Path] = []
    for raw in files:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (input_dir / candidate).resolve()
        resolved.append(candidate)
    return resolved


def make_case_id(prefix: str, pdf_path: Path) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower()).strip("-")
    token = token or "pdf"
    return f"{prefix}-{token}"


def write_json(path: Path, payload: Any) -> None:
    write_json_artifact(path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process one or more PDFs through the shared tax-server API."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="PDF files to upload. Defaults to all PDFs in --input-dir.",
    )
    parser.add_argument(
        "--input-dir",
        default=".",
        help="Directory containing input PDFs when positional files are omitted.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write per-file routing JSON plus a run manifest.",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="Purchased tax-server API key for this run.",
    )
    parser.add_argument(
        "--case-id-prefix",
        default="pdf-process",
        help="Prefix for generated case IDs sent to the API.",
    )
    parser.add_argument(
        "--disable-mistral-fallback",
        action="store_true",
        help="Disable the server-managed Mistral fallback for this run.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_paths = resolve_input_paths(input_dir, args.files)
    if not input_paths:
        raise SystemExit(f"No PDFs found in {input_dir}")

    created_at = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "created_at": created_at,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "use_mistral_fallback": not args.disable_mistral_fallback,
        "files": [],
    }

    manifest["base_url"] = TAX_SERVER_BASE_URL

    with TaxServerClient(api_key=args.api_key, timeout_seconds=300) as client:
        manifest["base_url"] = client.base_url
        try:
            manifest["health"] = client.health()
        except httpx.HTTPError as exc:
            manifest["health"] = {"error": str(exc)}
            manifest_path = output_dir / "process-manifest.json"
            write_json(manifest_path, manifest)
            print(f"Unable to reach tax-server at {client.base_url}: {exc}")
            print(f"Saved manifest to: {manifest_path}")
            return 1
        try:
            manifest["inspect"] = client.inspect_auth()
        except Exception as exc:  # pragma: no cover - depends on auth config
            manifest["inspect"] = {"error": str(exc)}

        for pdf_path in input_paths:
            pdf_path = pdf_path.resolve()
            case_id = make_case_id(args.case_id_prefix, pdf_path)
            entry: dict[str, Any] = {
                "pdf": str(pdf_path),
                "case_id": case_id,
            }

            if not pdf_path.exists():
                entry["status"] = "error"
                entry["error"] = f"File not found: {pdf_path}"
                manifest["files"].append(entry)
                print(f"[SKIP] {pdf_path.name}: file not found")
                continue

            artifact_base = output_dir / f"{pdf_path.stem}.routing.json"
            print(f"[UPLOAD] {pdf_path.name}")
            started = datetime.now(timezone.utc)
            try:
                response = client.process_pdf(
                    pdf_path,
                    case_id=case_id,
                    use_mistral_fallback=not args.disable_mistral_fallback,
                )
            except httpx.HTTPStatusError as exc:
                error_payload = {
                    "status_code": exc.response.status_code,
                    "error": exc.response.text.strip() or str(exc),
                }
                error_path = output_dir / f"{pdf_path.stem}.error.json"
                write_json(error_path, error_payload)
                entry.update(
                    {
                        "status": "error",
                        "elapsed_seconds": round(
                            (datetime.now(timezone.utc) - started).total_seconds(), 3
                        ),
                        "error_path": str(error_path),
                        **error_payload,
                    }
                )
                print(f"[ERROR] {pdf_path.name}: {error_payload['status_code']}")
                manifest["files"].append(entry)
                continue

            write_json(artifact_base, response)
            entry.update(
                {
                    "status": "ok",
                    "elapsed_seconds": round(
                        (datetime.now(timezone.utc) - started).total_seconds(), 3
                    ),
                    "output_path": str(artifact_base),
                    "job_id": response.get("job_id"),
                    "page_count": response.get("page_count"),
                    "result_uri": response.get("result_uri"),
                    "features_used": response.get("result", {}).get("features_used"),
                }
            )
            manifest["files"].append(entry)
            print(f"[OK] {pdf_path.name}: {entry['page_count']} pages")

    manifest_path = output_dir / "process-manifest.json"
    write_json(manifest_path, manifest)
    print(f"Saved manifest to: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
