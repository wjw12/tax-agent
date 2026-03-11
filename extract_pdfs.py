#!/usr/bin/env python3
"""
PDF text extraction script for tax documents.
Tries pdfplumber first, falls back to pdfminer, then PyPDF2.
Outputs raw extracted text per file so nothing is lost or fabricated.

Live-case rule:
- read raw PDFs from the active session source folder
- write extracted JSON to the durable case source-set extraction folder
"""

import argparse
import json
import os
import sys
from pathlib import Path

TAX_DIR = Path(__file__).parent

PDF_FILES = [
    "1099-DA.pdf",
    "1099-MISC.pdf",
    "2025-Individual-2037-Consolidated-Form-1099.pdf",
    "2025-Individual-TOD-3359-Consolidated-Form-1099.pdf",
    "2025_1099_Moomoo.pdf",
    "Discover-TaxForm-20260107-1099-INT.pdf",
]


def list_pdf_files(input_dir: Path) -> list[str]:
    return sorted(path.name for path in input_dir.glob("*.pdf") if path.is_file())


def extract_with_pdfplumber(path):
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            pages.append(
                {
                    "page": i + 1,
                    "text": text,
                    "tables": tables,
                }
            )
    return pages


def extract_with_pdfminer(path):
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextContainer

    pages = []
    for i, page_layout in enumerate(extract_pages(path)):
        lines = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                lines.append(element.get_text())
        pages.append({"page": i + 1, "text": "".join(lines), "tables": []})
    return pages


def extract_with_pypdf2(path):
    import PyPDF2

    pages = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({"page": i + 1, "text": text, "tables": []})
    return pages


def extract_pdf(path):
    errors = []
    for name, fn in [
        ("pdfplumber", extract_with_pdfplumber),
        ("pdfminer", extract_with_pdfminer),
        ("PyPDF2", extract_with_pypdf2),
    ]:
        try:
            pages = fn(path)
            return name, pages
        except Exception as e:
            errors.append(f"{name}: {e}")
    return "FAILED", [{"page": 0, "text": "", "tables": [], "errors": errors}]


def main():
    parser = argparse.ArgumentParser(description="Extract text from tax PDF files.")
    parser.add_argument(
        "file",
        nargs="?",
        help="Single PDF filename to process (e.g. 1099-DA.pdf). If omitted, all files are processed.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(TAX_DIR),
        help="Directory containing input PDFs (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for extracted_raw.json (default: input directory).",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        files_to_process = [args.file]
    elif input_dir == TAX_DIR:
        files_to_process = PDF_FILES
    else:
        files_to_process = list_pdf_files(input_dir)

    results = {}
    for fname in files_to_process:
        path = input_dir / fname
        if not path.exists():
            print(f"[SKIP] {fname} not found")
            results[fname] = {"error": "file not found"}
            continue

        print(f"\n{'=' * 60}")
        print(f"Extracting: {fname}")
        print(f"{'=' * 60}")

        method, pages = extract_pdf(str(path))
        print(f"  Method used: {method}")
        results[fname] = {"method": method, "pages": pages}

        for p in pages:
            if p.get("errors"):
                print(f"  [ERRORS]")
                for err in p["errors"]:
                    print(f"    {err}")
            print(f"\n  --- Page {p['page']} ---")
            print(p["text"])
            if p.get("tables"):
                for ti, table in enumerate(p["tables"]):
                    print(f"\n  [TABLE {ti + 1}]")
                    for row in table:
                        print(
                            "  "
                            + " | ".join(str(c) if c is not None else "" for c in row)
                        )

    # Also dump everything to a JSON file for downstream agents
    out_path = output_dir / "extracted_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n\nRaw extraction saved to: {out_path}")


if __name__ == "__main__":
    main()
