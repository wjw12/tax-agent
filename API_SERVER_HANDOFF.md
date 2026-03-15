# Tax Agent / Tax Server Boundary

## Purpose

This document describes the current system boundary between:

- `tax-agent`
  - this repository
  - a clean source package the customer runs locally with Codex or another
    compatible local agent
- `tax-server`
  - an authenticated backend API for PDF upload, OCR, and extraction storage

This replaces the older worker-orchestration model. There is no longer a remote
tax-agent worker daemon that performs end-to-end filing work on behalf of the
user.

## One-Sentence Model

`tax-agent` does the tax reasoning and PDF filling locally. `tax-server`
provides authenticated, synchronous PDF processing and returns raw extraction
artifacts for the local agent to consume.

## Current Product Shape

The current customer experience is:

1. the user downloads a clean `tax-agent` repo locally
2. the repo includes the blank 2025 tax forms and local agent instructions
3. the user provides their own uploaded PDFs at runtime
4. the local agent decides scope, asks questions, interprets facts, and fills
   forms locally
5. `tax-server`, when used, only helps with PDF processing and extraction

This repo should therefore ship:

- prompts and workflow docs
- deterministic tax logic
- empty 2025 forms
- maintenance scripts for the team

This repo should not ship:

- uploaded taxpayer PDFs
- sample source-form uploads
- generated OCR output
- live case workspaces

## Ownership Boundary

### `tax-agent` owns

- customer-facing intake and scope decisions
- supported-form schemas and validation in [src/models.py](/home/appuser/tax/src/models.py)
- audit sidecar schema in [src/audit_models.py](/home/appuser/tax/src/audit_models.py)
- supported form registry in [src/registry.py](/home/appuser/tax/src/registry.py)
- extraction-routing instructions in [workspace/PDF_ROUTING.md](/home/appuser/tax/workspace/PDF_ROUTING.md)
- audit methodology in [workspace/TAX_AUDIT_METHODOLOGY.md](/home/appuser/tax/workspace/TAX_AUDIT_METHODOLOGY.md)
- deterministic PDF field building and local PDF filling
- local artifact layout under `workspace/cases/<case-id>/...` when the user is
  working on a return

### `tax-server` owns

- API key validation and usage tracking
- PDF upload ingress
- synchronous page routing and extraction
- OCR and optional model fallback
- ephemeral storage lifecycle for uploads
- GCS storage for uploaded PDFs and extraction result JSON

### `tax-server` does not own

- tax reasoning
- supported-vs-unsupported filing decisions
- taxpayer interviews
- return completeness decisions
- final tax positions
- local PDF filling

## Current `tax-server` API Surface

Based on [tax-server/README.md](/home/appuser/tax-server/README.md) and
[docs/local-agent-backend-design.md](/home/appuser/tax-server/docs/local-agent-backend-design.md),
the current backend routes are:

- `GET /health`
- `POST /v1/auth/inspect`
- `POST /v1/pdf/process`

`POST /v1/pdf/process` is synchronous. It stores the uploaded PDF and the
result JSON in GCS, returns inline page extraction data, and records usage.

## Data Flow

When `tax-agent` uses `tax-server`:

1. the local agent uploads a PDF to `POST /v1/pdf/process`
2. `tax-server` validates the API key and processes the PDF
3. `tax-server` returns:
   - page results
   - extraction metadata
   - input/result object URIs
4. `tax-agent` uses those extraction artifacts locally
5. `tax-agent` continues taxpayer interaction, review, and local PDF filling

## Artifact Rules

Reference artifacts in this repo are limited to:

- `data/input/2025/`
- `2025-empty-forms/`

Live user work belongs under:

```text
workspace/cases/<case-id>/
  active.json
  sessions/<session-id>/
    source-pdfs/
  source-sets/<source-set-id>/
    extraction/
  data/input/2025/
  audit/
  filled-forms/2025/<run-id>/
```

Important separation:

- `sessions/<session-id>/source-pdfs/` is ephemeral local working storage
- uploaded source PDFs are user inputs, not repo fixtures
- extracted JSON may be retained locally per case
- blank forms in `2025-empty-forms/` are durable repo assets

## Integration Contract For `tax-agent`

If the local agent uses `tax-server`, it should send:

- an API key
- the PDF file
- a case identifier if needed by the backend contract
- extractor preferences only when the API supports them

It should expect back:

- a job or request identifier
- page count
- extraction results inline
- GCS URIs for the stored input and stored result
- usage summary

It should not expect:

- tax conclusions
- filled forms
- filing readiness decisions
- cross-form reconciliation

## Documentation Source Of Truth

For backend behavior, use:

- [tax-server/README.md](/home/appuser/tax-server/README.md)
- [docs/local-agent-backend-design.md](/home/appuser/tax-server/docs/local-agent-backend-design.md)

For local agent behavior in this repo, use:

- [AGENTS.md](/home/appuser/tax/AGENTS.md)
- [workspace/EXTRACTOR.md](/home/appuser/tax/workspace/EXTRACTOR.md)
- [workspace/REVIEW.md](/home/appuser/tax/workspace/REVIEW.md)
- [workspace/PDF_ROUTING.md](/home/appuser/tax/workspace/PDF_ROUTING.md)
- [workspace/TAX_AUDIT_METHODOLOGY.md](/home/appuser/tax/workspace/TAX_AUDIT_METHODOLOGY.md)
- [workspace/PDF_FILLING.md](/home/appuser/tax/workspace/PDF_FILLING.md)

## Local Client Config

This repo's shared client config lives in [src/tax_server_client.py](/home/appuser/tax/src/tax_server_client.py).

Current defaults:

- `DEFAULT_TAX_SERVER_BASE_URL = "http://34.10.4.155:8010"`
- `TAX_SERVER_BASE_URL` may override that default from the environment
- `TAX_SERVER_API_KEY` is read from the environment for authenticated routes
