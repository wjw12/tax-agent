# 2025 Federal Tax Prep Agent

A tax engine that works with coding agents.

Feed it a W-2, multiple 1099s, brokerage reports. It reads the PDFs, runs the calculations, and fills federal forms.

You can ask it to walk through deductions, adjust them, and see the math update in real time.

## What Makes This Different

Most tax-related AI demos lean on the model's training data for tax rules and math. That training data might be a year behind, and LLMs are unreliable at arithmetic.

This system takes a different approach:

- **Deterministic Python engine.** ~6,400 lines of Python code that computes every tax line mechanically. No LLM arithmetic. The agent calls the code; the code does the math.
- **28 form processors covering 4,200+ fields.** Every supported federal form has a registered model, processor, and PDF filler. Field mappings, inter-form wiring, and validation are all in code.
- **52,000+ lines of structured IRS data.** The actual 2025 tax tables, rate brackets, worksheets, and filing instructions are baked in as machine-readable JSON. Agents no longer rely on training data that might be stale.
- **Up-to-date 2025 filing rules.** Standard deduction amounts, Schedule 1-A (new for 2025), child credit changes, QBI thresholds, and other 2025-specific rules are embedded in the instruction set and constants. The agent instructions only add what falls outside an LLM's world knowledge.
- **Structured agent instructions.** The coordinator, sub-agents (extraction, deduction discovery, review, PDF filling), and their handoff contracts are fully specified. The agent follows a deterministic pipeline, not freeform reasoning.
- **Local and auditable.** All computation runs locally. Every payload has an audit sidecar. Every filled PDF has a verification report. The taxpayer can trace any number back to its source.

Works with any agent that can run a computer: Claude Code, Codex, OpenClaw, or similar.

## What This Repo Contains

- Customer-facing agent instructions in [AGENTS.md](./AGENTS.md)
- Sub-agent instructions in [workspace/](./workspace)
- Deterministic form models, processors, registry wiring, and PDF fill logic in [src/](./src)
- Reference sample payloads in [data/input/2025/](./data/input/2025)
- Blank 2025 IRS PDFs in [2025-empty-forms/](./2025-empty-forms)

## Scope

The system supports relatively straightforward individual returns:

- W-2 income, interest, dividends, basic stock sales
- Crypto sales, swaps, staking, mining, rewards, NFTs
- Schedule C self-employment / freelancer income
- Basic Schedule E rental real estate
- Federal filing including selected Form 1040-NR cases
- Supported state filing

It does not support S-corps, partnerships, C-corps, trusts, estates, FBAR/FATCA, or advanced real estate strategies. See [AGENTS.md](./AGENTS.md) for the full scope boundary.

## Runtime Expectations

This repo behaves as a source workspace. Local development uses the existing `.venv` and `uv`.

Install dependencies:

```bash
pip install -r requirements.txt
```

Or with uv:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api --help
```

## Backend Dependency

The local package uses a shared backend for PDF/OCR extraction work.

The API client lives in [src/tax_server_client.py](./src/tax_server_client.py), and the default extraction entrypoint lives in [src/process_pdfs_via_api.py](./src/process_pdfs_via_api.py).

The purchased API key is passed on each extraction run. The tax-server base URL is fixed in code at `https://tax.heurist.xyz`.

Example:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --api-key "$TAX_SERVER_API_KEY" \
  --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction
```

## Main Instruction Surface

Start with:

- [AGENTS.md](./AGENTS.md)

Supporting instruction files:

- [workspace/DEDUCTIONS.md](./workspace/DEDUCTIONS.md)
- [workspace/EXTRACTOR.md](./workspace/EXTRACTOR.md)
- [workspace/FORM_1040_2025_TAX.md](./workspace/FORM_1040_2025_TAX.md)
- [workspace/FORM_1040_2025_TAX_PLAN.md](./workspace/FORM_1040_2025_TAX_PLAN.md)
- [workspace/REVIEW.md](./workspace/REVIEW.md)
- [workspace/PDF_FILLING.md](./workspace/PDF_FILLING.md)

## Core Code Paths

The deterministic engine is centered on:

- [src/models.py](./src/models.py) -- form input models (Pydantic)
- [src/registry.py](./src/registry.py) -- form registration and wiring
- [src/processors.py](./src/processors.py) -- line-by-line computation
- [src/pdf_fillers.py](./src/pdf_fillers.py) -- PDF rendering and verification
- [src/pdf_mapping.py](./src/pdf_mapping.py) -- field-to-PDF-coordinate mapping
- [src/field_metadata.py](./src/field_metadata.py) -- field roles, inter-form wiring, build order
- [src/live_case_builder.py](./src/live_case_builder.py) -- payload construction with audit sidecars

Canonical PDF fill entrypoints live in [src/pdf_fillers.py](./src/pdf_fillers.py):

- `load_payload_for_pdf_fill(payload_path)` for one saved payload file
- `render_payload_pdf(payload, output_pdf_path)` for one validated payload
- `fill_case_forms(case_root, tax_year=2025, output_mode="verified" | "draft")` for the normal case-level run

TY2025 Form 1040 line 16 depends on committed local IRS data under [src/data/irs/2025/form_1040/](./src/data/irs/2025/form_1040/).

## Case Artifact Contract

Case-specific work belongs under:

```text
workspace/cases/<case-id>/
  active.json
  intake/
    deduction-leads.json
  sessions/<session-id>/source-pdfs/
  source-sets/<source-set-id>/extraction/
  data/input/<tax-year>/
  audit/
  filled-forms/<tax-year>/<run-id>/
```

Raw PDFs are treated as ephemeral session storage. Durable extraction artifacts, payload JSON, audit sidecars, and filled PDFs are the retained outputs.
