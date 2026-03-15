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

Default batch PDF processing now lives in:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction
```
