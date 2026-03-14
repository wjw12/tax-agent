# Tax Agent

Tax workflow workspace for local extraction review, audit, and deterministic PDF
filling for tax returns.

## Included

- extraction helpers: `extract_pdfs.py`, `ocr_extract.py`, `mistral_ocr.py`
- form models, processors, mappings, and fill logic in `src/`
- team maintenance commands in `scripts/`
- workflow docs in `AGENTS.md`, `workspace/`, and `API_SERVER_HANDOFF.md`
- reference sample inputs in `data/input/2025/`
- blank 2025 tax forms in `2025-empty-forms/`

## Not Included

- local virtualenv and Codex state
- generated OCR outputs
- live case workspaces
- uploaded taxpayer source PDFs
- ad hoc local test files
- secrets from `.env`

## Local Setup

Create a local `.env` if needed. A template is provided in `.env.example`.

Use the existing workspace environment pattern from `AGENTS.md`:

```bash
uv run --python .venv/bin/python --no-project ...
```
