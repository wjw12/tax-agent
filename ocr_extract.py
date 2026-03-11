#!/usr/bin/env python3
"""
Enhanced PDF extraction using:
  - GMFT  : financial table detection/extraction (broker statements)
  - PaddleOCR : primary OCR engine (handles scrambled-font PDFs)
  - pytesseract: OCR fallback
Outputs to ocr_extracted.json

Live-case rule:
- read raw PDFs from the active session source folder
- write OCR JSON to the durable case source-set extraction folder
"""

import argparse
import json
import os
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

# These files have scrambled font encodings and need OCR instead of text extraction
OCR_ONLY_FILES = {
    "Discover-TaxForm-20260107-1099-INT.pdf",
}


def list_pdf_files(input_dir: Path) -> list[str]:
    return sorted(path.name for path in input_dir.glob("*.pdf") if path.is_file())


# ---------------------------------------------------------------------------
# GMFT – financial table extraction
# ---------------------------------------------------------------------------


def extract_tables_gmft(path: str) -> list[dict]:
    """
    Run GMFT table detection + formatting on every page.
    Returns a list of {page, tables} dicts where each table has
    'markdown' and 'records' keys.
    """
    from gmft.auto import AutoTableDetector, AutoTableFormatter
    from gmft.pdf_bindings import PyPDFium2Document

    detector = AutoTableDetector()
    formatter = AutoTableFormatter()
    doc = PyPDFium2Document(str(path))
    page_results = []

    try:
        for i, page in enumerate(doc):
            tables = []
            for cropped in detector.extract(page):
                try:
                    ft = formatter.extract(cropped)
                    df = ft.df()
                    tables.append(
                        {
                            "markdown": df.to_markdown(index=False),
                            "records": df.to_dict(orient="records"),
                        }
                    )
                except Exception as e:
                    tables.append({"error": str(e)})
            page_results.append({"page": i + 1, "tables": tables})
    finally:
        doc.close()

    return page_results


# ---------------------------------------------------------------------------
# OCR engines
# ---------------------------------------------------------------------------


def ocr_with_paddleocr(path: str) -> list[dict]:
    """Convert each page to an image and run PaddleOCR (2.7.x API)."""
    import numpy as np
    from paddleocr import PaddleOCR
    from pdf2image import convert_from_path

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    images = convert_from_path(str(path), dpi=300)

    pages = []
    for i, img in enumerate(images):
        img_array = np.array(img)
        result = ocr.ocr(img_array, cls=True)
        lines = []
        if result and result[0]:
            for line in result[0]:
                lines.append(line[1][0])
        pages.append({"page": i + 1, "text": "\n".join(lines)})

    return pages


def ocr_with_tesseract(path: str) -> list[dict]:
    """Fallback OCR using pytesseract."""
    import pytesseract
    from pdf2image import convert_from_path

    images = convert_from_path(str(path), dpi=300)
    pages = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        pages.append({"page": i + 1, "text": text})

    return pages


def run_ocr(path: str) -> tuple[str, list[dict]]:
    """Try PaddleOCR first, fall back to tesseract."""
    for name, fn in [
        ("paddleocr", ocr_with_paddleocr),
        ("tesseract", ocr_with_tesseract),
    ]:
        try:
            pages = fn(path)
            return name, pages
        except Exception as e:
            print(f"  [OCR] {name} failed: {e}")
    return "FAILED", []


def run_all_ocr(path: str) -> dict[str, list[dict]]:
    """Run both PaddleOCR and tesseract independently, return both results."""
    results = {}
    for name, fn in [
        ("paddleocr", ocr_with_paddleocr),
        ("tesseract", ocr_with_tesseract),
    ]:
        try:
            pages = fn(path)
            results[name] = pages
            print(f"  OCR [{name}]: {len(pages)} pages")
        except Exception as e:
            results[name] = [{"page": 0, "text": "", "error": str(e)}]
            print(f"  OCR [{name}] failed: {e}")
    return results


# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------


def extract_pdf(path: str, force_ocr: bool = False) -> dict:
    result: dict = {
        "gmft_tables": None,
        "ocr_method": None,
        "ocr_pages": None,
        "paddleocr_pages": None,
        "tesseract_pages": None,
        "errors": [],
    }

    # ---- GMFT tables (always attempted unless force_ocr) -------------------
    if not force_ocr:
        try:
            gmft_pages = extract_tables_gmft(path)
            result["gmft_tables"] = gmft_pages
            table_count = sum(len(p["tables"]) for p in gmft_pages)
            print(f"  GMFT : {len(gmft_pages)} pages, {table_count} tables found")
        except Exception as e:
            result["errors"].append(f"gmft: {e}")
            print(f"  GMFT failed: {e}")

    # ---- OCR (both engines independently) ----------------------------------
    ocr_results = run_all_ocr(path)
    result["paddleocr_pages"] = ocr_results.get("paddleocr")
    result["tesseract_pages"] = ocr_results.get("tesseract")

    # best available for backward-compat ocr_pages / ocr_method fields
    if ocr_results.get("paddleocr") and not ocr_results["paddleocr"][0].get("error"):
        result["ocr_method"] = "paddleocr"
        result["ocr_pages"] = ocr_results["paddleocr"]
    elif ocr_results.get("tesseract") and not ocr_results["tesseract"][0].get("error"):
        result["ocr_method"] = "tesseract"
        result["ocr_pages"] = ocr_results["tesseract"]

    return result


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------


def print_result(fname: str, result: dict) -> None:
    paddle_pages = result.get("paddleocr_pages") or []
    tess_pages = result.get("tesseract_pages") or []
    gmft_pages = result.get("gmft_tables") or []

    # Side-by-side OCR comparison per page
    max_pages = max(len(paddle_pages), len(tess_pages))
    for i in range(max_pages):
        ppage = paddle_pages[i] if i < len(paddle_pages) else {}
        tpage = tess_pages[i] if i < len(tess_pages) else {}
        pg_num = ppage.get("page") or tpage.get("page") or i + 1

        if ppage.get("error"):
            print(f"\n  --- Page {pg_num} [PaddleOCR FAILED] {ppage['error'][:120]}")
        else:
            ptext = ppage.get("text", "").strip()
            print(f"\n  --- Page {pg_num} [PaddleOCR] ---")
            print(ptext[:600] + (" …" if len(ptext) > 600 else ""))

        ttext = tpage.get("text", "").strip()
        print(f"\n  --- Page {pg_num} [Tesseract] ---")
        print(ttext[:600] + (" …" if len(ttext) > 600 else ""))

    # GMFT tables
    for pg in gmft_pages:
        for ti, t in enumerate(pg["tables"]):
            if "error" in t:
                print(f"\n  [Page {pg['page']} TABLE {ti + 1} ERROR] {t['error']}")
            elif t.get("markdown"):
                print(f"\n  [Page {pg['page']} TABLE {ti + 1}]")
                md = t["markdown"]
                print(md[:1200] + (" …" if len(md) > 1200 else ""))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract tax PDFs with GMFT (tables) + OCR (text)."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Single PDF filename to process (e.g. 1099-DA.pdf). "
        "Omit to process all files.",
    )
    parser.add_argument(
        "--ocr-only",
        action="store_true",
        help="Skip GMFT and run OCR only (useful for quick text checks).",
    )
    parser.add_argument(
        "--input-dir",
        default=str(TAX_DIR),
        help="Directory containing input PDFs (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for OCR JSON outputs (default: input directory).",
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
    all_results: dict = {}

    for fname in files_to_process:
        path = input_dir / fname
        if not path.exists():
            print(f"\n[SKIP] {fname} – file not found")
            all_results[fname] = {"error": "file not found"}
            continue

        print(f"\n{'=' * 60}")
        print(f"Processing: {fname}")
        print(f"{'=' * 60}")

        force_ocr = args.ocr_only or (fname in OCR_ONLY_FILES)
        result = extract_pdf(str(path), force_ocr=force_ocr)
        all_results[fname] = result

        print_result(fname, result)

    # Persist everything — one combined file plus a paddle-only file for easy diffing
    out_path = output_dir / "ocr_extracted.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n\nSaved full results to: {out_path}")

    # Separate paddle vs tesseract comparison file
    comparison: dict = {}
    for fname, data in all_results.items():
        comparison[fname] = {
            "paddleocr": data.get("paddleocr_pages"),
            "tesseract": data.get("tesseract_pages"),
        }
    cmp_path = output_dir / "ocr_comparison.json"
    with open(cmp_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
    print(f"Saved OCR comparison to: {cmp_path}")


if __name__ == "__main__":
    main()
