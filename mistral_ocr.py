#!/usr/bin/env python3
"""
================================================================================
MISTRAL OCR — AGENT HANDOFF GUIDE
Tax PDF extraction experiment using Mistral Small 2503 (vision) on GCP Vertex AI
================================================================================

PROJECT CONTEXT
---------------
We are testing whether Mistral's multimodal vision model produces cleaner
text extraction than the previous methods (pdfplumber, PaddleOCR, Tesseract)
on a set of six 2025 US tax 1099 PDFs. Three files are confirmed "challenging":
one has a scrambled font encoding that defeats all text-layer extractors, one
has a garbled two-column layout, and one is a dense 10-page brokerage statement.

All files live in the same directory as this script:
    /home/appuser/tax/

For live-case worker use, do not treat this repo layout as the output
convention. Read raw PDFs from the active session source folder and write
retained OCR JSON to the case `source-sets/<source-set-id>/extraction/`
folder.


DIRECTORY LAYOUT
----------------
/home/appuser/tax/
  ├── mistral_ocr.py                  ← THIS SCRIPT
  │
  ├── — INPUT PDFs —
  ├── 1099-DA.pdf                     Coinbase digital-asset sales (2 pages)
  ├── 1099-MISC.pdf                   Coinbase miscellaneous income (2 pages)
  ├── 2025-Individual-2037-Consolidated-Form-1099.pdf   Fidelity acct 2037 (4 pages)
  ├── 2025-Individual-TOD-3359-Consolidated-Form-1099.pdf  Fidelity TOD acct (8 pages)
  ├── 2025_1099_Moomoo.pdf            Moomoo brokerage consolidated (10 pages)
  ├── Discover-TaxForm-20260107-1099-INT.pdf  Discover/CapitalOne interest (3 pages)
  │
  ├── — PREVIOUS EXTRACTION RESULTS (inputs for comparison) —
  ├── extracted_raw.json              pdfplumber / pdfminer / PyPDF2 results
  ├── ocr_extracted.json              GMFT tables + PaddleOCR + Tesseract (full)
  ├── ocr_comparison.json             PaddleOCR vs Tesseract side-by-side (compact)
  │
  ├── — THIS SCRIPT'S OUTPUT —
  ├── mistral_ocr_results.json        Written after each run (overwritten each time)
  │
  ├── — SOURCE SCRIPTS —
  ├── extract_pdfs.py                 Produced extracted_raw.json
  ├── ocr_extract.py                  Produced ocr_extracted.json + ocr_comparison.json
  └── sample-codemistralai_intro.py   GCP Vertex Mistral reference notebook (converted)


EXISTING RESULT FILE SCHEMAS
-----------------------------

extracted_raw.json  (from extract_pdfs.py — pdfplumber/pdfminer/PyPDF2)
    {
      "<filename>.pdf": {
        "method": "pdfplumber",          # whichever succeeded first
        "pages": [
          { "page": 1, "text": "...", "tables": [[row, ...], ...] },
          ...
        ]
      }
    }

ocr_extracted.json  (from ocr_extract.py — GMFT + PaddleOCR + Tesseract)
    {
      "<filename>.pdf": {
        "gmft_tables": [                 # GMFT financial table detector
          { "page": 1, "tables": [{ "markdown": "...", "records": [...] }] }
        ],
        "ocr_method": "paddleocr",       # best method that succeeded
        "ocr_pages":  [ { "page": 1, "text": "..." } ],   # best method's output
        "paddleocr_pages": [ { "page": 1, "text": "..." } ],
        "tesseract_pages": [ { "page": 1, "text": "..." } ],
        "errors": []
      }
    }

ocr_comparison.json  (from ocr_extract.py — compact head-to-head)
    {
      "<filename>.pdf": {
        "paddleocr": [ { "page": 1, "text": "..." }, ... ],
        "tesseract":  [ { "page": 1, "text": "..." }, ... ]
      }
    }

mistral_ocr_results.json  (THIS SCRIPT — written on every run)
    {
      "<filename>.pdf": {
        "model":    "mistral-ocr-2505",
        "location": "us-central1",
        "dpi":      200,
        "pages": [
          {
            "page": 1,
            "text": "...",               # full extracted text
            "prompt_tokens":     1234,   # token usage for cost tracking
            "completion_tokens":  456,
            "total_tokens":      1690
          },
          ...
        ]
      }
    }
    NOTE: if a page fails, its entry contains "error": "<message>" and "text": "".


KNOWN PER-FILE ISSUES (from previous OCR runs)
-----------------------------------------------

1. Discover-TaxForm-20260107-1099-INT.pdf  ← WORST OFFENDER
   Problem : Page 1 has a scrambled/private font encoding. The PDF text layer
             is completely unreadable. pdfplumber extracts garbled characters.
             PaddleOCR page 1 output includes nonsense like:
               "uffsyt aocq", "requrem ent boxys alhe ked. the payerqs reportin"
             Tesseract page 1 reads the instructions column correctly but still
             mangles the form-data column (the actual 1099-INT box values).
   Pages 2-3: Clean — page 2 is the itemised interest breakdown, page 3 is FAQ.
   Key value to verify: Box 1 Interest income = $1,220.91 (account 7040973552)

2. 1099-DA.pdf  (Coinbase digital assets)
   Problem : Two-column layout on page 1. PaddleOCR merges left+right columns
             mid-sentence causing scrambled reading order. The account/document
             ID ("R0DLI1Q8DHDQEUTMW0GU") is embedded inline with the name field
             producing "Jiewen Wang I R0DLI1Q8DHDQEUTMW0GU" instead of separating
             name from ID. The "$10,oo0" typo (two lowercase o's instead of zeros)
             appears in PaddleOCR output — check if Mistral reads it correctly.
   Key value to verify: 1f-Proceeds = $315,990.05, USDC, 50 transactions.

3. 2025_1099_Moomoo.pdf  (Moomoo brokerage)
   Problem : 10 pages, dense two-column layout with many sub-tables. Previous
             OCR actually worked reasonably well on most pages, making this a
             good regression/baseline test. Page 3 contains the 1099-B stock
             sale data (COIN 50 shares, proceeds $14,494.99, basis $3,726.00).
   Key value to verify: Total long-term gain $10,768.99; TLT dividends $1,523.94.

4. 2025-Individual-2037-Consolidated-Form-1099.pdf  (Fidelity acct 2037)
   Problem : 4 pages. GMFT detected tables but the markdown output had garbled
             column headers. pdfplumber worked reasonably. This file is NOT in
             the default CHALLENGING_FILES list — add it manually if needed.
   Key value to verify: 1a Total Ordinary Dividends = $3,004.17.

5. 2025-Individual-TOD-3359-Consolidated-Form-1099.pdf  (Fidelity TOD acct)
   Problem : 8 pages. Similar to above but longer. Complex capital gains tables.
             NOT in the default CHALLENGING_FILES list.

6. 1099-MISC.pdf  (Coinbase miscellaneous)
   Problem : Minimal — this file extracted cleanly with pdfplumber. Included
             for completeness. NOT in the default CHALLENGING_FILES list.
   Key value to verify: Box 3 Other income = $2,947.36.


STEP-BY-STEP SETUP
-------------------

Step 1 — Install uv (if not already present):
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv is already installed at /home/appuser/.local/bin/uv

Step 2 — Authenticate with GCP (one-time per machine):
    gcloud auth application-default login
    # This creates ~/.config/gcloud/application_default_credentials.json
    # The script calls google.auth.default() which reads that file automatically.
    # Alternatively, point to a service account key:
    #   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json

Step 3 — Set required environment variable:
    export GCP_PROJECT_ID=your-gcp-project-id

Step 4 — Optional env var overrides:
    export GCP_LOCATION=us-central1       # or europe-west4 (both support the model)
    export MISTRAL_MODEL=mistral-ocr-2505

Step 5 — Verify poppler is installed (required by pdf2image):
    pdftoppm -v      # should print version; if not: apt-get install -y poppler-utils
    # poppler was already used by the previous OCR scripts so it should be present.

Step 6 — No virtual environment needed. uv reads the inline [script] metadata
    at the top of this file and installs dependencies into an isolated cache
    automatically on first run. Subsequent runs reuse the cache.


HOW TO RUN
----------

    # Default: the 3 challenging files (fastest, ~15-30 API calls total)
    uv run /home/appuser/tax/mistral_ocr.py

    # Just the single worst offender (Discover, 3 pages, 3 API calls):
    uv run /home/appuser/tax/mistral_ocr.py Discover-TaxForm-20260107-1099-INT.pdf

    # Two specific files:
    uv run /home/appuser/tax/mistral_ocr.py Discover-TaxForm-20260107-1099-INT.pdf 1099-DA.pdf

    # All six PDFs (29 pages total, ~29 API calls, takes several minutes):
    uv run /home/appuser/tax/mistral_ocr.py --all

    # Higher DPI — better for fine print, larger image payload, slower:
    uv run /home/appuser/tax/mistral_ocr.py --dpi 300

    # Try the EU region if us-central1 is slow or unavailable:
    uv run /home/appuser/tax/mistral_ocr.py --location europe-west4

    # Suppress the inline Tesseract/PaddleOCR comparison printout:
    uv run /home/appuser/tax/mistral_ocr.py --no-compare

    # Combine flags freely:
    uv run /home/appuser/tax/mistral_ocr.py --all --dpi 300 --location europe-west4

The script prints a live progress line per page and a 900-char preview of the
extracted text. Full results are always written to mistral_ocr_results.json.


HOW TO COMPARE RESULTS AFTER RUNNING
--------------------------------------

The script already prints a 500-char side-by-side snippet for page 1 of each
file at the end of each file's section (Mistral vs Tesseract vs PaddleOCR).
For deeper analysis, use the approaches below.

--- APPROACH 1: Quick Python diff in the terminal ---

Run this one-liner after the script finishes to compare page 1 of the Discover
file — the most important test case:

    python3 - <<'EOF'
    import json
    mistral = json.load(open("/home/appuser/tax/mistral_ocr_results.json"))
    cmp     = json.load(open("/home/appuser/tax/ocr_comparison.json"))
    raw     = json.load(open("/home/appuser/tax/extracted_raw.json"))

    fname = "Discover-TaxForm-20260107-1099-INT.pdf"
    print("=== MISTRAL ===")
    print(mistral[fname]["pages"][0]["text"][:1500])
    print("\n=== TESSERACT ===")
    print(cmp[fname]["tesseract"][0]["text"][:1500])
    print("\n=== PADDLEOCR ===")
    print(cmp[fname]["paddleocr"][0]["text"][:1500])
    print("\n=== PDFPLUMBER ===")
    print(raw[fname]["pages"][0]["text"][:1500])
    EOF

Change `fname` to any of the six PDF filenames to inspect a different file.
Change `[0]` to `[1]`, `[2]`, etc. to inspect later pages.

--- APPROACH 2: Key-value spot-checks ---

These are the critical dollar amounts and identifiers that MUST appear verbatim
in a correctly extracted page. Use them as a checklist:

    python3 - <<'EOF'
    import json

    mistral = json.load(open("/home/appuser/tax/mistral_ocr_results.json"))

    CHECKS = {
        "Discover-TaxForm-20260107-1099-INT.pdf": {
            "page": 1,
            "must_contain": ["1,220.91", "7040973552", "72-0210640", "XXX-XX-9508",
                             "CAPITAL ONE", "1099-INT"],
        },
        "1099-DA.pdf": {
            "page": 2,
            "must_contain": ["315,990.05", "QQKDMF6N9", "USDC", "50",
                             "455293997", "1099-DA"],
        },
        "2025_1099_Moomoo.pdf": {
            "page": 1,
            "must_contain": ["1,523.94", "14,494.99", "3,726.00", "10,768.99",
                             "37-1801571", "1007212890766763"],
        },
    }

    for fname, spec in CHECKS.items():
        if fname not in mistral:
            print(f"[SKIP] {fname} not in results"); continue
        page_data = next(
            (p for p in mistral[fname]["pages"] if p["page"] == spec["page"]), {}
        )
        text = page_data.get("text", "")
        print(f"\n{'='*60}\n{fname}  (page {spec['page']})")
        for val in spec["must_contain"]:
            found = val in text
            print(f"  {'OK  ' if found else 'MISS'} {val!r}")
    EOF

--- APPROACH 3: Character-count and token-cost summary ---

    python3 - <<'EOF'
    import json

    mistral = json.load(open("/home/appuser/tax/mistral_ocr_results.json"))
    cmp     = json.load(open("/home/appuser/tax/ocr_comparison.json"))

    print(f"{'FILE':<52} {'PAGES':>5}  {'MISTRAL':>8}  {'TESS':>8}  {'PADDLE':>8}  {'TOK$':>8}")
    print("-" * 100)
    for fname, data in mistral.items():
        pages = data.get("pages", [])
        m_chars = sum(len(p.get("text","")) for p in pages)
        m_tokens = sum((p.get("total_tokens") or 0) for p in pages)
        cmp_entry = cmp.get(fname, {})
        t_chars = sum(len(p.get("text","")) for p in (cmp_entry.get("tesseract") or []))
        p_chars = sum(len(p.get("text","")) for p in (cmp_entry.get("paddleocr") or []))
        # rough cost estimate placeholder; verify current Mistral OCR pricing in Vertex docs
        cost_est = m_tokens / 1_000_000 * 0.10
        print(f"{fname:<52} {len(pages):>5}  {m_chars:>8}  {t_chars:>8}  {p_chars:>8}  ${cost_est:>7.4f}")
    EOF

--- APPROACH 4: Write a structured diff to a file for offline review ---

    python3 - <<'EOF'
    import json, textwrap

    mistral = json.load(open("/home/appuser/tax/mistral_ocr_results.json"))
    cmp     = json.load(open("/home/appuser/tax/ocr_comparison.json"))
    raw     = json.load(open("/home/appuser/tax/extracted_raw.json"))

    out_lines = []
    for fname in mistral:
        out_lines.append(f"\n{'#'*80}\n# {fname}\n{'#'*80}")
        pages_m = mistral[fname].get("pages", [])
        pages_t = (cmp.get(fname) or {}).get("tesseract", [])
        pages_r = (raw.get(fname) or {}).get("pages", [])
        n = max(len(pages_m), len(pages_t), len(pages_r))
        for i in range(n):
            out_lines.append(f"\n## Page {i+1}")
            for label, pages in [("MISTRAL", pages_m), ("TESSERACT", pages_t), ("PDFPLUMBER", pages_r)]:
                text = pages[i].get("text","").strip() if i < len(pages) else "(no data)"
                out_lines.append(f"\n--- {label} ---\n{text}\n")
    open("/home/appuser/tax/ocr_diff_report.txt", "w").write("\n".join(out_lines))
    print("Written: /home/appuser/tax/ocr_diff_report.txt")
    EOF

    Then open ocr_diff_report.txt and visually scan each section.


WHAT "GOOD" LOOKS LIKE — EVALUATION RUBRIC
--------------------------------------------

Score each file/page combination on these criteria:

  CRITICAL (must pass for the result to be usable):
  ✓ All dollar amounts present and correct (no digit transpositions)
  ✓ All form box numbers present (Box 1, 1a, 1b, 3, etc.)
  ✓ Payer TIN and Recipient TIN present (even if partially masked)
  ✓ Account numbers present and ungarbled
  ✓ No text from a different page bleeding in

  IMPORTANT:
  ✓ Reading order is logical (box label immediately followed by its value)
  ✓ Two-column layouts are handled without mid-sentence merges
  ✓ Numbers that look similar are not confused ($10,000 vs $10,oo0)
  ✓ Footnote markers (1, 2, *, †) retained and associated with correct text

  NICE-TO-HAVE:
  ✓ Blank/separator lines between logical sections
  ✓ Rotated stamps like "Copy B" captured
  ✓ Reasonable character count vs Tesseract (within 20% is fine)


NEXT STEPS FOR CONTINUED EVALUATION
-------------------------------------

1. Re-run with --dpi 300 on the Discover file specifically and compare whether
   the garbled page 1 improves further.

2. Try --location europe-west4 if us-central1 results look truncated — model
   deployments can differ slightly between regions.

3. If Mistral OCR on the Discover page 1 still misses box values, consider a
   two-pass approach: send the image twice with different crop regions (left
   half / right half) to isolate the two-column form layout.

4. Extend the key-value spot-check (Approach 2 above) to all six files and
   write the pass/fail results into a structured evaluation JSON. This becomes
   the ground-truth test fixture for any further extraction pipeline work.

5. Compare token counts across files to estimate per-file API cost. The
   prompt_tokens field in mistral_ocr_results.json includes the image tokens
   (vision models charge for image pixels as tokens).

6. If results are good enough, the next integration step is to feed
   mistral_ocr_results.json into the tax summary pipeline that reads from
   extracted_raw.json today (see workspace/2025_TAX_SUMMARY.md).
"""

import argparse
import base64
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

import google.auth
import google.auth.credentials
from google.auth.transport.requests import Request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAX_DIR = Path(__file__).parent

# Files that caused trouble for PaddleOCR / Tesseract:
#   - Discover: scrambled font encoding → garbled text on page 1
#   - Coinbase 1099-DA: garbled name / account-ID fields
#   - Moomoo: 10-page dense consolidated statement (good baseline for comparison)
CHALLENGING_FILES = [
    "Discover-TaxForm-20260107-1099-INT.pdf",
    "1099-DA.pdf",
    "2025_1099_Moomoo.pdf",
]

ALL_FILES = [
    "1099-DA.pdf",
    "1099-MISC.pdf",
    "2025-Individual-2037-Consolidated-Form-1099.pdf",
    "2025-Individual-TOD-3359-Consolidated-Form-1099.pdf",
    "2025_1099_Moomoo.pdf",
    "Discover-TaxForm-20260107-1099-INT.pdf",
]

KEY_VALUE_CHECKS: dict[str, dict[str, Any]] = {
    "Discover-TaxForm-20260107-1099-INT.pdf": {
        "must_contain": [
            "1,220.91",
            "7040973552",
            "72-0210640",
            "XXX-XX-9508",
            "CAPITAL ONE",
            "1099-INT",
        ]
    },
    "1099-DA.pdf": {
        "must_contain": [
            "315,990.05",
            "QQKDMF6N9",
            "USDC",
            "50",
            "455293997",
            "1099-DA",
            "R0DLI1Q8DHDQEUTMW0GU",
        ]
    },
    "2025_1099_Moomoo.pdf": {
        "must_contain": [
            "1,523.94",
            "14,494.99",
            "3,726.00",
            "10,768.99",
            "37-1801571",
            "1007212890766763",
            "TLT",
        ]
    },
}

# Vertex AI endpoint template
VERTEX_ENDPOINT_TPL = (
    "https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations"
    "/{region}/publishers/mistralai/models/{model}:rawPredict"
)

# System prompt tuned for verbatim tax-document extraction
OCR_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert OCR system specialised in US tax documents (1099 series,
    brokerage statements, bank interest forms).

    Your sole task: extract ALL text that appears in the provided image, exactly
    as printed — no interpretation, no summarisation, no commentary.

    Rules:
    • Preserve every number, dollar amount, date, form-box label, and identifier.
    • Read left-to-right, top-to-bottom; separate logical sections with a blank line.
    • For multi-column layouts, complete the left column before the right column
      so that box labels and their values stay together.
    • If text is rotated or stamped (e.g. "Copy B"), include it in brackets: [Copy B].
    • Do NOT add headers, footers, or any text not present in the image.
    • Output plain text only — no Markdown, no JSON.
""")

OCR_USER_PROMPT = "Extract all text from this tax document page."

# How many characters to show per page in the inline preview
PREVIEW_CHARS = 900


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


def list_pdf_files(input_dir: Path) -> list[str]:
    return sorted(path.name for path in input_dir.glob("*.pdf") if path.is_file())

# ---------------------------------------------------------------------------
# GCP / Vertex helpers
# ---------------------------------------------------------------------------


def make_credentials() -> google.auth.credentials.Credentials:
    """Return refreshed ADC credentials scoped for Vertex AI."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    return creds


def bearer_token(creds: google.auth.credentials.Credentials) -> str:
    """Return a valid access token, refreshing if it has expired."""
    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def build_endpoint_url(project_id: str, region: str, model: str) -> str:
    return VERTEX_ENDPOINT_TPL.format(region=region, project=project_id, model=model)


# ---------------------------------------------------------------------------
# PDF → document payload
# ---------------------------------------------------------------------------


def pdf_to_base64_document_url(pdf_path: str) -> str:
    """Return a data URL for the original PDF bytes."""
    pdf_bytes = Path(pdf_path).read_bytes()
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"data:application/pdf;base64,{b64_pdf}"


# ---------------------------------------------------------------------------
# Mistral OCR call
# ---------------------------------------------------------------------------


def call_mistral_ocr(
    pdf_document_url: str,
    endpoint_url: str,
    creds: google.auth.credentials.Credentials,
    model: str,
) -> dict[str, Any]:
    """
    POST a PDF document to the Mistral OCR endpoint on Vertex AI and return
    the parsed JSON response.

    Raises requests.HTTPError on non-2xx responses.
    """
    import requests  # noqa: PLC0415

    payload: dict[str, Any] = {
        "model": model,
        "document": {
            "type": "document_url",
            "document_url": pdf_document_url,
        },
        "include_image_base64": False,
    }

    headers = {
        "Authorization": f"Bearer {bearer_token(creds)}",
        "Content-Type": "application/json",
    }

    response = requests.post(endpoint_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def process_pdf(
    pdf_path: str,
    endpoint_url: str,
    creds: google.auth.credentials.Credentials,
    model: str,
    dpi: int,
) -> list[dict[str, Any]]:
    """
    Send *pdf_path* to Mistral OCR and return per-page result dicts.
    Returns a list of per-page result dicts.
    """
    print("  Encoding PDF for OCR …", end=" ", flush=True)
    try:
        pdf_document_url = pdf_to_base64_document_url(pdf_path)
    except Exception as exc:
        print(f"FAILED\n  {exc}")
        return [{"page": 0, "text": "", "error": str(exc)}]
    print("done")

    print("  Calling Mistral OCR … ", end="", flush=True)
    try:
        resp = call_mistral_ocr(pdf_document_url, endpoint_url, creds, model)
        print("ok")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return [{"page": 0, "text": "", "error": str(exc)}]

    usage: dict[str, Any] = resp.get("usage_info", {})
    pages: list[dict[str, Any]] = []
    resp_pages = resp.get("pages") or []
    if not resp_pages:
        return [
            {
                "page": 0,
                "text": "",
                "error": f"Unexpected OCR response: missing pages field: {resp!r}",
            }
        ]

    for fallback_page_num, page_data in enumerate(resp_pages, start=1):
        page_index = page_data.get("index", fallback_page_num)
        page_num = page_index + 1 if isinstance(page_index, int) else fallback_page_num
        page_text = page_data.get("markdown", "") or ""
        pages.append(
            {
                "page": page_num if isinstance(page_num, int) else fallback_page_num,
                "text": page_text,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            }
        )

    return pages


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_separator(label: str = "", width: int = 70) -> None:
    if label:
        pad = width - len(label) - 3
        print(f"\n{'=' * 3} {label} {'=' * max(pad, 0)}")
    else:
        print("=" * width)


def print_page_preview(pages: list[dict[str, Any]]) -> None:
    for page in pages:
        pg = page.get("page", "?")
        if page.get("error"):
            print(f"\n  [Page {pg} — ERROR] {page['error']}")
            continue
        text = (page.get("text") or "").strip()
        preview = text[:PREVIEW_CHARS]
        truncated = len(text) > PREVIEW_CHARS
        print(f"\n  ── Page {pg} {'─' * 50}")
        print(textwrap.indent(preview + (" …" if truncated else ""), "  "))


def load_comparison_data(output_dir: Path) -> dict[str, Any]:
    """Load the existing PaddleOCR / Tesseract comparison JSON if available."""
    cmp_path = output_dir / "ocr_comparison.json"
    if cmp_path.exists():
        with open(cmp_path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def print_comparison(
    fname: str, mistral_pages: list[dict[str, Any]], cmp_data: dict[str, Any]
) -> None:
    """Side-by-side first-page comparison: Mistral vs Tesseract vs PaddleOCR."""
    existing = cmp_data.get(fname)
    if not existing:
        return

    mistral_p1 = next(
        (p.get("text", "") for p in mistral_pages if p.get("page") == 1), ""
    )

    print_separator("COMPARISON — Page 1", width=70)
    cols = [
        ("Mistral (this run)", mistral_p1),
        ("Tesseract (prev)", _first_page_text(existing.get("tesseract"))),
        ("PaddleOCR (prev)", _first_page_text(existing.get("paddleocr"))),
    ]
    for label, text in cols:
        snippet = (text or "").strip()[:500]
        print(f"\n  [{label}]")
        print(textwrap.indent(snippet or "(empty)", "    "))


def _first_page_text(pages: list[Any] | None) -> str:
    if not pages:
        return ""
    first = pages[0] if pages else {}
    return first.get("text", "") if isinstance(first, dict) else ""


def print_key_value_summary(all_results: dict[str, Any]) -> None:
    """Print a compact pass/fail summary for known key values."""
    printed = False
    for fname, spec in KEY_VALUE_CHECKS.items():
        result = all_results.get(fname)
        if not result:
            continue

        pages = result.get("pages") or []
        text = "\n".join(page.get("text", "") for page in pages)
        if not printed:
            print_separator("KEY VALUE SUMMARY", width=70)
            printed = True
        print(f"\n  {fname}")
        for needle in spec["must_contain"]:
            found = needle in text
            status = "OK  " if found else "MISS"
            print(f"    {status} {needle}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    load_local_env(TAX_DIR / ".env")

    parser = argparse.ArgumentParser(
        description=(
            "Test Mistral OCR (GCP Vertex AI) on challenging tax PDFs.\n"
            "Results saved to mistral_ocr_results.json in the same directory."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "PDF filename(s) to process (basename only, e.g. 1099-DA.pdf). "
            "Defaults to the three known-challenging files."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all six PDF files, not just the challenging ones.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI for PDF-to-image rasterisation (default: 200).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("MISTRAL_MODEL", "mistral-ocr-2505"),
        help=(
            "Mistral model on Vertex AI "
            "(default: mistral-ocr-2505). "
            "Env var: MISTRAL_MODEL."
        ),
    )
    parser.add_argument(
        "--location",
        default=os.getenv("GCP_LOCATION", "us-central1"),
        help=(
            "GCP Vertex AI region "
            "(default: us-central1; also try europe-west4). "
            "Env var: GCP_LOCATION."
        ),
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Skip the side-by-side comparison with previous OCR results.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(TAX_DIR),
        help="Directory containing input PDFs (default: script directory).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for mistral_ocr_results.json (default: input directory).",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_dir
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Validate required env var ----------------------------------------
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    if not project_id:
        print(
            "ERROR: GCP_PROJECT_ID is not set.\n"
            "  export GCP_PROJECT_ID=your-gcp-project-id\n"
            "  then re-run."
        )
        sys.exit(1)

    # ---- Decide which files to process ------------------------------------
    if args.all:
        files_to_process = ALL_FILES
    elif args.files:
        files_to_process = args.files
    elif input_dir != TAX_DIR:
        files_to_process = list_pdf_files(input_dir)
    else:
        files_to_process = CHALLENGING_FILES

    # ---- Banner -----------------------------------------------------------
    print_separator()
    print("  Mistral OCR  ·  GCP Vertex AI")
    print(f"  Model    : {args.model}")
    print(f"  Region   : {args.location}")
    print(f"  Project  : {project_id}")
    print(f"  DPI      : {args.dpi}")
    print(f"  Files    : {files_to_process}")
    print_separator()

    # ---- GCP credentials --------------------------------------------------
    print("\nObtaining GCP Application Default Credentials …", end=" ", flush=True)
    try:
        creds = make_credentials()
        print("ok")
    except Exception as exc:
        print(f"FAILED\n  {exc}")
        print(
            "\nMake sure you are authenticated:\n"
            "  gcloud auth application-default login\n"
            "or set GOOGLE_APPLICATION_CREDENTIALS to a service-account key file."
        )
        sys.exit(1)

    endpoint_url = build_endpoint_url(project_id, args.location, args.model)
    print(f"Endpoint : {endpoint_url}\n")

    # ---- Optional: load previous results for comparison ------------------
    cmp_data = {} if args.no_compare else load_comparison_data(output_dir)

    # ---- Process each file -----------------------------------------------
    all_results: dict[str, Any] = {}

    for fname in files_to_process:
        pdf_path = input_dir / fname
        if not pdf_path.exists():
            print(f"\n[SKIP] {fname}  — not found at {pdf_path}")
            all_results[fname] = {"error": "file not found"}
            continue

        print_separator(fname)

        pages = process_pdf(
            str(pdf_path),
            endpoint_url,
            creds,
            model=args.model,
            dpi=args.dpi,
        )

        all_results[fname] = {
            "model": args.model,
            "location": args.location,
            "dpi": args.dpi,
            "pages": pages,
        }

        # Preview extracted text
        print_page_preview(pages)

        # Side-by-side comparison with previous OCR
        if not args.no_compare:
            print_comparison(fname, pages, cmp_data)

    # ---- Persist results --------------------------------------------------
    out_path = output_dir / "mistral_ocr_results.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(all_results, fh, indent=2, ensure_ascii=False)

    print_key_value_summary(all_results)

    print_separator()
    print(f"Saved results  →  {out_path}")


if __name__ == "__main__":
    main()
