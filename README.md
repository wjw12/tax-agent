# Tax Agent

Tax workflow workspace for local extraction review, audit, and deterministic PDF
filling for tax returns.

## Included

- PDF/API integration and extraction helpers in `src/`
- form models, processors, mappings, and fill logic in `src/`
- team maintenance commands in `scripts/`
- workflow docs in `AGENTS.md`, `workspace/`, and `API_SERVER_HANDOFF.md`
- reference sample inputs in `data/input/2025/`
- blank 2025 tax forms in `2025-empty-forms/`, including `1040`, `1040-SR`, and `1040-NR`

## Not Included

- local virtualenv and Codex state
- generated OCR outputs
- live case workspaces
- uploaded taxpayer source PDFs
- ad hoc local test files
- secrets from `.env`

## Local Setup

Create a local `.env` if needed. A template is provided in `.env.example`.
`src/tax_server_client.py` auto-loads this repo-local `.env` for tax-server settings.

For the shared backend PDF/OCR service, this repo now uses:

- `TAX_SERVER_BASE_URL`
  - defaults to `http://34.10.4.155:8010`
- `TAX_SERVER_API_KEY`
  - required for `POST /v1/auth/inspect` and `POST /v1/pdf/process`

Use the existing workspace environment pattern from `AGENTS.md`:

```bash
uv run --python .venv/bin/python --no-project ...
```

Main prompt and sub-agent docs:

- `AGENTS.md` for intake and coordinator behavior
- `workspace/DEDUCTIONS.md` for deduction and common tax-benefit discovery
- `workspace/EXTRACTOR.md` and `workspace/PDF_ROUTING.md` for the extraction sub-agent
- `workspace/REVIEW.md` and `workspace/TAX_AUDIT_METHODOLOGY.md` for the review sub-agent
- `workspace/PDF_FILLING.md` for the PDF filling sub-agent
- `src/tax_constants_2025.py` for structured 2025 amounts and thresholds
- targeted 2025 supplements in `workspace/FORM_1099_DA.md`,
  `workspace/SCHEDULE_1A_2025.md`, `workspace/CHILD_CREDITS_2025.md`,
  `workspace/FORM_1099_K_2025.md`,
  `workspace/SCHEDULE_C_2025_DELTAS.md`,
  `workspace/FORM_8962_2025.md`, and
  `workspace/FORM_1040_NR_2025_DELTAS.md`

Default batch PDF processing now lives in:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction
```
