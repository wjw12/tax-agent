# Tax Agent

Tax workflow workspace for extraction, audit, and deterministic IRS PDF filling.

## Included

- extraction helpers: `extract_pdfs.py`, `ocr_extract.py`, `mistral_ocr.py`
- form models, processors, mappings, and fill logic in `src/`
- workflow docs in `AGENTS.md`, `workspace/`, and `docs/`
- reference sample inputs in `data/input/2025/`
- blank IRS forms in `2025-empty-forms/`
- reference source PDFs in `2025-source-forms/`

## Not Included

- local virtualenv and Codex state
- generated OCR outputs
- live case workspaces
- ad hoc local test files
- secrets from `.env`

## Local Setup

Create a local `.env` if needed. A template is provided in `.env.example`.

Use the existing workspace environment pattern from `AGENTS.md`:

```bash
uv run --python .venv/bin/python --no-project ...
```
