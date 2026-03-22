# Tax Agent

This repo is the shipped local source package for the tax filing agent system.

For the broader architecture, see:

- [/home/appuser/tax-frontend/docs/system-masterdoc.md](/home/appuser/tax-frontend/docs/system-masterdoc.md)

## What This Repo Contains

- customer-facing instructions in [/home/appuser/tax/AGENTS.md](/home/appuser/tax/AGENTS.md)
- sub-agent instructions in [/home/appuser/tax/workspace](/home/appuser/tax/workspace)
- deterministic form models, processors, registry wiring, and PDF fill logic in [/home/appuser/tax/src](/home/appuser/tax/src)
- reference sample payloads in [/home/appuser/tax/data/input/2025](/home/appuser/tax/data/input/2025)
- blank 2025 IRS PDFs in [/home/appuser/tax/2025-empty-forms](/home/appuser/tax/2025-empty-forms)

## What This Repo Does Not Contain

The shipped artifact intentionally excludes local-only runtime data such as:

- `.env`
- `.venv`
- `tmp/`
- `workspace/cases/`
- local override files and scratch artifacts

Packaging is driven by [/home/appuser/tax/.gitignore](/home/appuser/tax/.gitignore) through the frontend packager in [/home/appuser/tax-frontend/scripts/package-tax-release.ts](/home/appuser/tax-frontend/scripts/package-tax-release.ts).
The packager stages files from the current worktree and skips tracked paths that no longer exist locally.

## Runtime Expectations

This repo currently behaves like a source workspace rather than a polished standalone Python package.

Observed realities in the inspected tree:

- local development uses the existing `.venv`
- docs and commands assume `uv run --python .venv/bin/python --no-project`
- `uv.lock` exists locally but is not part of the shipped artifact
- no `pyproject.toml` was present in this repo during inspection

## Backend Dependency

The local package expects a shared backend for PDF/OCR work.

The API client lives in [/home/appuser/tax/src/tax_server_client.py](/home/appuser/tax/src/tax_server_client.py), and the default extraction entrypoint lives in [/home/appuser/tax/src/process_pdfs_via_api.py](/home/appuser/tax/src/process_pdfs_via_api.py).

The shipped repo no longer includes a local `.env.example`.
Operators are expected to pass the purchased API key on each extraction run.
The tax-server base URL is fixed in code at `https://tax.heurist.xyz`.
That purchased key is what the buyer receives after Stripe fulfillment.

Example:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api \
  --api-key "$TAX_SERVER_PURCHASED_KEY" \
  --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs \
  --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction
```

## Main Instruction Surface

Start with:

- [/home/appuser/tax/AGENTS.md](/home/appuser/tax/AGENTS.md)

Supporting instruction files:

- [/home/appuser/tax/workspace/DEDUCTIONS.md](/home/appuser/tax/workspace/DEDUCTIONS.md)
- [/home/appuser/tax/workspace/EXTRACTOR.md](/home/appuser/tax/workspace/EXTRACTOR.md)
- [/home/appuser/tax/workspace/REVIEW.md](/home/appuser/tax/workspace/REVIEW.md)
- [/home/appuser/tax/workspace/PDF_FILLING.md](/home/appuser/tax/workspace/PDF_FILLING.md)

## Core Code Paths

The deterministic engine is centered on:

- [/home/appuser/tax/src/models.py](/home/appuser/tax/src/models.py)
- [/home/appuser/tax/src/registry.py](/home/appuser/tax/src/registry.py)
- [/home/appuser/tax/src/processors.py](/home/appuser/tax/src/processors.py)
- [/home/appuser/tax/src/pdf_fillers.py](/home/appuser/tax/src/pdf_fillers.py)
- [/home/appuser/tax/src/field_metadata.py](/home/appuser/tax/src/field_metadata.py)
- [/home/appuser/tax/src/live_case_builder.py](/home/appuser/tax/src/live_case_builder.py)

Canonical PDF fill entrypoints live in
[/home/appuser/tax/src/pdf_fillers.py](/home/appuser/tax/src/pdf_fillers.py):

- `load_payload_for_pdf_fill(payload_path)` for one saved payload file
- `render_payload_pdf(payload, output_pdf_path)` for one validated payload
- `fill_case_forms(case_root, tax_year=2025, output_mode="verified" | "draft")`
  for the normal case-level run that writes PDFs, `fill-manifest.json`, and
  `verification-report.json`

`build_pdf_fill_plan(...)` is the inspection/debug helper. It is not the normal
render entrypoint.

## Case Artifact Contract

Case-specific work belongs under:

```text
workspace/cases/<case-id>/
  sessions/<session-id>/source-pdfs/
  source-sets/<source-set-id>/extraction/
  data/input/<tax-year>/
  filled-forms/<tax-year>/<run-id>/
```

Raw PDFs are treated as ephemeral session storage. Durable extraction artifacts, payload JSON, audit sidecars, and filled PDFs are the retained outputs.

## Testing And Demos

Synthetic scenarios and integration tooling live in:

- [/home/appuser/tax-test/tooling](/home/appuser/tax-test/tooling)

That tooling imports the real modules from this repo and validates the same artifact contract you plan to ship.
