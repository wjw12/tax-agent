# PDF Page Routing — Technical Design

## Problem

Not all PDF pages are the same. Running every page through the same extraction
method wastes compute, misses data, or produces garbage. A routing phase
classifies each page before handing it to the right extractor.

For the main agent and extraction sub-agent, this also means attached files are
not treated as resolved facts until the relevant file has actually been routed
and its usable contents have been read. A mere file reference, unread upload,
or placeholder blob does not satisfy intake.

---

## Four Page Classes

| Class | Description | Extractor |
|---|---|---|
| **digital-text** | Native text layer, clean encoding | pdfplumber |
| **garbled-text** | Native text layer, broken font encoding | Tesseract OCR, then server-managed Mistral fallback if validation fails |
| **image-scan** | Page is a raster image, no text layer | Tesseract OCR, then server-managed Mistral fallback if validation fails |
| **table-heavy** | Structured grid data dominates the page | GMFT + pdfplumber |

Handwriting is excluded from scope: IRS tax documents are never handwritten at
the page level. Annotations (handwritten sticky notes, signature fields) can be
flagged and skipped without affecting core data extraction.

---

## Detection Signals

### 1. Text-layer presence
Use `pdfplumber` to extract the text layer. Count characters.

```
char_count = len(page.extract_text() or "")
```

- `char_count < 50` on a full page → no usable text layer → **image-scan**
- `char_count >= 50` → text layer exists, proceed to encoding check

### 2. Garbled-font detection
Broken font encoding produces many isolated single-character tokens separated
by spaces. Two fast heuristics applied to the extracted text:

**a. Short-token ratio**
```
tokens = text.split()
short_token_ratio = sum(1 for t in tokens if len(t) == 1) / max(len(tokens), 1)
```
`short_token_ratio > 0.6` → **garbled-text**

**b. Space density**
```
space_density = text.count(" ") / max(len(text), 1)
```
`space_density > 0.4` → **garbled-text**

Either threshold firing is sufficient to reroute to OCR.

### 3. Table density
Run `pdfplumber`'s table finder on the page (cheap — no ML inference).

```
tables = page.find_tables()
table_coverage = sum(t.bbox[3] - t.bbox[1] for t in tables) / page.height
```

`table_coverage > 0.25` (tables cover >25% of page height) → tag as
**table-heavy** and also invoke GMFT alongside the text extractor.

Note: table-heavy is an additive tag, not an exclusive class. A digital-text
page can also be table-heavy.

### 4. Image-only confirmation
Before committing to full OCR, confirm the page is truly imagistic:

```
images = page.images          # from pdfplumber
has_images = len(images) > 0
```

Low char count + `has_images=True` → **image-scan** (high confidence).  
Low char count + `has_images=False` → blank page, skip.

---

## Routing Decision Tree

```
extract text layer (pdfplumber)
│
├─ char_count < 50
│   ├─ has images → image-scan  → Tesseract OCR
│   └─ no images → blank        → skip
│
└─ char_count >= 50
    ├─ short_token_ratio > 0.6
    │   or space_density > 0.4  → garbled-text → Tesseract OCR
    │
    └─ clean text
        ├─ table_coverage > 0.25 → table-heavy  → pdfplumber + GMFT
        └─ otherwise             → digital-text → pdfplumber only
```

---

## Recommended Stack

| Layer | Tool | Why |
|---|---|---|
| Page parsing baseline | `pdfplumber` | Fast, no dependencies, exact text layer |
| Garble detection | Heuristics on pdfplumber output | Zero overhead, no extra library |
| Raster OCR | `tesseract` via `pytesseract` + `pdf2image` | Reliable, outperformed PaddleOCR on these docs |
| AI OCR fallback | tax-server managed Mistral fallback | Better fallback than PaddleOCR for complex layouts and image-like tax pages |
| Financial table extraction | `gmft` (AutoTableDetector + AutoTableFormatter) | Best structured output for broker statements |
| Image presence check | `pdfplumber` `.images` attribute | Already loaded, no extra cost |

**PaddleOCR is not recommended.** If a second OCR engine is needed after
tesseract, prefer **Mistral OCR** over PaddleOCR. On this document set,
PaddleOCR was the least reliable on garbled-font pages and adds heavy
dependency constraints (PaddlePaddle, numpy<2, oneDNN CPU compatibility
issues).

**Mistral OCR is not the default extractor.** Use the tax-server API as the
default extraction path and let it decide when to apply OCR, table extraction,
and any server-managed fallback. Native text extraction is still more exact on
Fidelity, Moomoo, and Morgan Stanley statements.

---

## API Processing

Use the shared tax-server API for extraction runs that write into
`workspace/cases/<case-id>/`:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --api-key "<issued-tax-server-key>" \
  --input-dir ./workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir ./workspace/cases/case-001/source-sets/source-set-001/extraction
```

The `--api-key` value is the paid tax-server key issued after checkout. The
repo does not bundle that secret or a local `.env` template for it. The target
backend is fixed in code at `https://tax.heurist.xyz`.

Disable the server-managed Mistral fallback only when you need a stricter
baseline comparison:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --api-key "<issued-tax-server-key>" \
  --input-dir ./workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir ./workspace/cases/case-001/source-sets/source-set-001/extraction \
  --disable-mistral-fallback
```

Expected response contract:

- Per-file routing and extraction JSON is written to `<pdf-stem>.routing.json`.
- A batch manifest is written to `process-manifest.json`.
- The server returns page results inline and stores durable object URIs for
  uploaded inputs and routing outputs.

Agent rule of thumb:

- Use `pdfplumber` first when text is already extractable.
- Use `tesseract` first for garbled-text and image-scan pages.
- Escalate to the server-managed Mistral fallback only when key fields are
  missing, reading order is broken, or local OCR disagreement is high.

---

## Implementation Notes

- **Routing is per-page, not per-file.** A single Fidelity consolidated 1099
  has digital-text pages, table-heavy pages, and a blank trailer page — all in
  one file.

- **GMFT model load is expensive (~2 s cold start).** Load
  `AutoTableDetector` and `AutoTableFormatter` once at process startup and
  reuse across all pages.

- **OCR is expensive (~1–3 s/page at 300 dpi).** Only invoke when the router
  flags a page as image-scan or garbled-text. For this document set that is
  currently one file (Discover 1099-INT page 1) and partial pages on the
  Coinbase 1099-DA.

- **Server-managed Mistral fallback is more expensive than local OCR.** It adds
  network and per-page model cost. Use it after baseline extraction fails
  validation rather than as the default first pass.

- **Validation gates matter more than model choice.** For 1099s and W-2s,
  always check for payer TIN, masked recipient TIN, account number, tax year,
  and box values before accepting OCR output.

- **Confidence score.** Emit a `router_confidence` field per page
  (`high / medium / low`) based on how far the metrics are from the thresholds.
  Pages near a boundary should be logged for manual review.

- **Thresholds are tunable.** Start with the values above. After processing
  more documents, fit them against a small labeled sample if classification
  errors appear.

---

## Output Schema per Page

```json
{
  "source_set_id": "src_2026_03_11_01",
  "file": "2025-Individual-TOD-3359-Consolidated-Form-1099.pdf",
  "page": 3,
  "class": "table-heavy",
  "tags": ["digital-text", "table-heavy"],
  "router_confidence": "high",
  "char_count": 1840,
  "short_token_ratio": 0.04,
  "space_density": 0.12,
  "table_coverage": 0.61,
  "extractor": ["pdfplumber", "gmft"]
}
```

---

## Persistence Rule

This workflow separates ephemeral raw PDFs from durable extracted artifacts.

- raw PDFs may exist only during the active user session
- raw PDFs may be deleted when the user disconnects and the session lease ends
- persisted extraction JSON under the case `source-sets/` folder is the
  retained source of truth for later review and PDF filling work
- other sub-agents should not require the original PDF once the retained
  extraction artifacts have been written successfully

Recommended durable extraction layout:

```text
workspace/cases/<case-id>/
  source-sets/<source-set-id>/
    manifest.json
    extraction/
      process-manifest.json
      <pdf-stem>.routing.json
      <pdf-stem>.error.json
```

`manifest.json` should include at least:

- `source_set_id`
- `session_id`
- `created_at`
- `files`
- `file_sha256`
- `page_count` when known
- `tax_year_hint` when known

When raw PDFs are later purged, the extraction JSON plus the source-set
manifest become the retained evidence base for audit and fill decisions.

---

## Agent Autonomy, Fixed Output

The agent may decide autonomously how to handle a source PDF:

- run Python scripts
- run shell commands
- use the tax-server API and its routed extraction stack
- retry with a different extractor when validation fails

**Do not require a rigid input schema for the source PDFs.** The folder can
contain mixed document types, mixed page classes, and partial statement sets.

**Do require a rigid output contract.** No matter how the agent extracted the
data, it must always produce:

- one durable extraction record for the active `source_set_id`
- one model-compatible form payload file
- one evidence-bearing audit sidecar file

### Contract split

There are **two different schemas** in this workflow.

#### 1. Final form payload

For payloads saved under `workspace/cases/<case-id>/`, this is written to:

`workspace/cases/<case-id>/data/input/<tax-year>/<form>.json`

Rules:

- It must validate against the matching Pydantic model in `src/models.py`
- It must remain minimal and computation-oriented
- Do **not** add `status`, `sources`, `computations`, `issues`, or other audit metadata at the root
- It MUST include EVERY top-level model field explicitly, even when the value
  is `0`, `null`, `false`, or `[]`
- Extra keys not declared by the model are FORBIDDEN

Examples already present in `data/input/2025/*.json` are reference samples for
shape only. They are not the default destination for output under
`workspace/cases/<case-id>/` and should not be overwritten.

#### 2. Audit sidecar

This is written next to the form payload under `workspace/cases/<case-id>/`:

`workspace/cases/<case-id>/data/input/<tax-year>/<form>.audit.json`

Rules:

- It contains evidence and computation traceability
- It does **not** replace the final form payload
- It may reference the form payload path, but should not duplicate the whole filing pipeline contract unless needed for transient in-memory work

#### 3. Durable extraction record

This is written under the active source set:

`workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`

Rules:

- It is the retained source of truth after raw PDF purge
- It should preserve router decisions and extractor outputs
- It should be append-only per source set; do not silently rewrite prior source
  sets in place
- It should include enough metadata for later `.audit.json` sidecars to cite the
  correct source set and page

### Runtime extraction result

During execution, the agent may keep an in-memory object that contains both the
evidence and the final `form_payload`.

That runtime object is not the same thing as the persisted `.json` filing
payload or the persisted extraction record.

Every document-to-form step may use a runtime object with these fields:

- `status` — one of `accepted`, `needs_review`, `blocked`
- `sources` — source references that tie output keys to file/page locations
- `computations` — optional derived values computed in Python
- `issues` — missing values, conflicts, unreadable pages, unresolved tax-rule questions
- `form_payload` — final minimal JSON payload for the later form processor

### Non-negotiable rule

Every numeric value in the final form payload must point to one of:

- a retained source location in the persisted extraction record for a
  `source_set_id`
- a Python computation trace built from previously accepted source entries

LLM-only guesses are never acceptable for numeric tax values.
That computation trace must come from Python code, and the code must import and
depend on the relevant modules under `src/` whenever repo code exists for the
calculation.
Any agent-authored Python file used for that computation must be stored under
`scripts/`.
If a registered processor exists for the form, derived values MUST come from
that executable path rather than from hand-written arithmetic.

### Runtime shape

```json
{
  "status": "accepted",
  "sources": [],
  "computations": [],
  "issues": [],
  "form_payload": {}
}
```

### Field constraints

#### Final form payload

- Must validate against the corresponding model in `src/models.py`
- Must preserve the existing field names and nesting used by `data/input/2025/*.json`
- JSON numbers are accepted here for backward compatibility with the current sample files and model parsing

#### Audit sidecar

- Should be validated separately from the form payload
- Should contain `status`, `sources`, optional `computations`, and `issues`
- Prefer string serialization for money-like decimal values

#### `status`

- `accepted` — extraction and validation passed
- `needs_review` — partial success, but a human must review before filing
- `blocked` — cannot safely produce a filing payload

#### `computations`

Each computation should include:

- `output_key`
- `inputs`
- `python_expression`
- `result`

Rules:

- All arithmetic must be reproducible in Python
- Financial math must use `decimal.Decimal`, not `float`
- If a value cannot be computed safely, emit an `issue` and mark the result for review

#### `sources`

Each source entry should include:

- `source_set_id`
- `output_key`
- `value` — optional extracted value or summary
- `file`
- `file_sha256` — preferred when available
- `page`
- `locator` — nearby label, box name, or table description
- `extractor`
- `router_confidence`

#### `issues`

Each issue should include:

- `code`
- `severity`
- `message`
- `related_keys`

Recommended issue codes:

- `missing_field`
- `conflicting_values`
- `ocr_unreliable`
- `basis_missing`
- `manual_tax_rule_review`

### Example output

#### Example final form payload

```json
{
  "form_code": "1040-Schedule-1",
  "tax_year": 2025,
  "additional_income_items": [
    {
      "description": "1099-MISC other income",
      "amount": 2947.36
    }
  ],
  "adjustment_items": []
}
```

#### Example audit sidecar

```json
{
  "schema_version": "1.0",
  "form_code": "1040-Schedule-1",
  "tax_year": 2025,
  "status": "accepted",
  "sources": [
    {
      "source_set_id": "src_2026_03_11_01",
      "output_key": "additional_income_items[0].amount",
      "value": "2947.36",
      "file": "1099-MISC.pdf",
      "file_sha256": "abc123...",
      "page": 1,
      "locator": "Box 3 Other income",
      "extractor": "pdfplumber",
      "router_confidence": "high"
    }
  ],
  "computations": [
    {
      "output_key": "schedule_1_line_10_total",
      "inputs": ["additional_income_items[0].amount"],
      "python_expression": "Decimal('2947.36')",
      "result": "2947.36"
    }
  ],
  "issues": [],
  "form_path": "workspace/cases/case-001/data/input/2025/1040-schedule-1.json"
}
```

### Output path convention

Write retained extraction outputs under the active source set:

`workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`

Write the final minimal form payload to the active case location:

`workspace/cases/<case-id>/data/input/2025/1040-schedule-1.json`

Write the evidence sidecar next to it:

`workspace/cases/<case-id>/data/input/2025/1040-schedule-1.audit.json`

The sidecar should contain `status`, `sources`, optional `computations`, and
`issues`. Keep it minimal. The form payload file should remain compatible with
`src/models.py`.

The sidecar should cite the `source_set_id` used for every retained source
reference.

### Sample file rule

Do not overwrite files in `data/input/2025/`.

Those files are canonical examples and regression fixtures. Live extraction
work belongs under `workspace/cases/<case-id>/`.

---

## What This Solves

| Problem observed | Router fix |
|---|---|
| Discover page 1 garbage text | garbled-text → Tesseract, then Mistral if key fields still missing |
| Coinbase 1099-DA name field garbled | garbled-text → Tesseract, then Mistral if layout remains scrambled |
| Fidelity tables missed by pdfplumber | table-heavy → GMFT added |
| Blank trailer pages (Moomoo p.10, Fidelity p.8) | blank → skip |
| Full OCR run on clean-text files | digital-text → skip OCR entirely |
