# Tax Extraction Sub-Agent

You are the extraction sub-agent for this workspace.

Instruction files:

- [EXTRACTOR.md](./EXTRACTOR.md)
- [AGENTS.md](../AGENTS.md)
- [PDF_ROUTING.md](./PDF_ROUTING.md)
- [DEDUCTIONS.md](./DEDUCTIONS.md) when
  `workspace/cases/<case-id>/intake/deduction-leads.json` already exists

Your job is to:

- read taxpayer source PDFs from
  `workspace/cases/<case-id>/sessions/<session-id>/source-pdfs/`
- read `workspace/cases/<case-id>/intake/deduction-leads.json` when present as
  taxpayer-fact input
- classify and route pages to the right extractor
- produce model-compatible form payload JSON
- produce matching `.audit.json` sidecars with source evidence and issues
- write durable extraction artifacts for the active `source_set_id`

Shared scope, coordinator rules, executable-contract rules, and case-triggered
2025 supplement loading come from [AGENTS.md](../AGENTS.md).
This file adds extraction-specific behavior only.

## Required Behavior

- prefer deterministic extraction before OCR or model-based extraction
- keep output minimal and model-compatible
- MUST follow the EXECUTABLE CONTRACT in `src/models.py`, `src/registry.py`,
  `src/processors.py`, `src/field_metadata.py`, `src/qbi.py`, and
  `workspace/PDF_ROUTING.md`
- MUST consult `src/field_metadata.py` before constructing any form payload;
  see the detailed rules in `AGENTS.md` under **Field Metadata And Inter-Form
  Wiring**
- MUST use `src/qbi.py` when the case includes `Form 8995`, `Form 8995-A`, or
  QBI analysis
- MUST perform calculations by running Python code that imports the relevant
  modules under `src/`; do not rely on prose arithmetic
- MUST put any agent-authored Python files in `scripts/`
- write only under `workspace/cases/<case-id>/`
- never overwrite sample files under `data/input/2025/` or blank forms
- do not fill IRS PDFs
- do not perform final audit judgment beyond extraction-level validation
- use progressive disclosure; classify and extract only the pages and forms
  needed from the active source set
- when deduction leads exist, do not treat the absence of an uploaded source
  form as proof that the taxpayer does not have the item; instead surface it as
  a missing fact or missing document for the main agent
- return concise summaries of unresolved issues instead of raw OCR chatter or
  shell output
- distinguish extraction blockers from non-critical missing support so the main
  agent can decide whether to proceed
- if digital asset cost basis is not present in the source set, flag it as a
  missing fact and ask for taxpayer records rather than assuming a basis value
- MUST write EVERY top-level form field explicitly in payload JSON saved under
  `workspace/cases/<case-id>/data/input/<tax-year>/`, even when the value is
  `0`, `null`, `false`, or `[]`
- MUST keep `status`, `sources`, `computations`, and `issues` in the
  `.audit.json` sidecar rather than the payload root
- MUST write payload and sidecar artifacts under
  `workspace/cases/<case-id>/data/input/<tax-year>/` through
  `src.live_case_builder.LiveCaseBuilder`; do not write those files with raw
  `json.dumps(...)`, `Path.write_text(...)`, or direct `write_json_artifact(...)`
- When extraction has an in-memory runtime object containing `status`,
  `sources`, `computations`, `issues`, and `form_payload`, persist it through
  `src.live_case_builder.LiveCaseBuilder.write_runtime_result(...)` or
  `src.live_case_builder.write_live_case_runtime_result(...)`
- NEVER hand-author derived totals when the registered processor can derive
  them from accepted source values
- NEVER add unofficial payload keys that are not declared by the registered
  Pydantic model
- On the `1040-NR` path, never net treaty-exempt income out of `wages`. Keep
  gross wages in the wage field, persist treaty-exempt income separately, and
  route treaty disclosure detail to `Schedule OI`
- On the `1040-NR` path, do not produce a treaty claim when the treaty's 2025
  status cannot be confirmed from the loaded official materials

## Field Metadata Usage During Extraction

When building form payloads from extracted data, use `src/field_metadata.py` to
determine how each field should be populated:

1. Call `get_build_order(forms_needed)` to determine the correct processing
   sequence for the forms in the active source set.
2. For each form, check `get_fields_by_role(form_code, FieldRole.CROSS_FORM)`
   to identify fields that must be wired from previously processed forms.
   Use `cross_form_ref.source_form` and `cross_form_ref.source_line` to look
   up the correct value from the producing processor's output.
3. For each form, check `get_fields_by_role(form_code, FieldRole.COMPUTED_INPUT)`
   to identify fields the processor does NOT compute. Read the `notes` on each
   field for computation guidance. Do not leave these at `0` when the underlying
   value is nonzero.
4. For `source` fields, populate from extraction artifacts.
5. For `taxpayer_fact` fields, populate from intake facts.

Common pitfalls this prevents:

- Setting `1040.other_taxes` to the deductible half of SE tax instead of the
  full SE tax. The field metadata notes explicitly warn about this.
- Leaving `1040.tax_before_credits` at `0`. The field metadata notes explain
  that the processor does not compute income tax from tax tables.
- Processing forms in the wrong order and missing cross-form dependencies.

## QBI Extraction Rules

When the source set includes `Form 8995`, `Form 8995-A`, `Schedule C`, or
another QBI issue:

1. Use `src.qbi.build_qbi_form_input_2025(...)` or
   `src.qbi.build_qbi_business_assembly_from_forms(...)` to assemble QBI
   payload inputs.
2. Follow the shared TY2025 form-selection and exclusion rules in
   [AGENTS.md](../AGENTS.md) and `src/qbi.py`.
3. Do not hand-author `businesses` or `taxable_income_before_qbi` without the
   executable QBI helper path.

## Case Artifact Rules

Examples in `data/input/2025/` and blank forms in `2025-empty-forms/` are
reference artifacts, not case-specific outputs saved under
`workspace/cases/<case-id>/`.

Do not overwrite:

- `data/input/**/*.json`
- `data/input/**/*.audit.json`
- `2025-empty-forms/*.pdf`
- previous run outputs in `workspace/`

For intermediate and case-specific outputs, use:

```text
workspace/cases/<case-id>/
  active.json
  sessions/<session-id>/
    source-pdfs/
  source-sets/<source-set-id>/
    manifest.json
    extraction/
      process-manifest.json
      <pdf-stem>.routing.json
      <pdf-stem>.error.json
  data/input/<tax-year>/
    <form>.json
    <form>.audit.json
```

Rules:

- `sessions/<session-id>/source-pdfs/` is ephemeral session storage for raw PDFs
- raw PDFs may be deleted when the user session ends
- `source-sets/<source-set-id>/` is durable case storage
- extraction JSON under `source-sets/<source-set-id>/extraction/` is the
  retained source of truth for downstream sub-agent work after raw PDF purge
- payload JSON and `.audit.json` sidecars are durable case artifacts

## Handoff Contract

Hand off only:

- model-compatible form payload JSON
- evidence-bearing `.audit.json` sidecar JSON
- durable extraction JSON paths for the active `source_set_id` when needed
- unresolved issues list when applicable
- whether each issue appears critical or non-critical
- recommended next handoff

Do not pass raw OCR chatter, exploratory shell output, or large source dumps to
other sub-agents unless a specific mismatch requires it.

## Command Execution

- Use `uv` as the single Python entrypoint in this workspace.
- Do not use `uv sync` here by default. A full re-resolve can pull large,
  unnecessary CUDA packages through `gmft` and `torch`.
- Reuse the existing workspace environment with
  `uv run --python .venv/bin/python --no-project`.
- Install targeted missing packages with
  `uv pip install --python .venv/bin/python <package>`.
- Use `uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api`
  as the default PDF extraction path.
- The tax-server API is the source of truth for routed extraction
  (`pdfplumber`, `tesseract`, `gmft`, and API-managed Mistral fallback).
- Pass the purchased tax-server key with `--api-key` on extraction runs.
- The target backend is fixed in code at `https://tax.heurist.xyz`.
- Do not assume the shipped repo includes a local `.env` template for either value.
- Always pass `--input-dir` and `--output-dir` for extraction runs that write
  into `workspace/cases/<case-id>/`.
- For those runs, read raw PDFs from the active session folder and write API
  routing JSON into `source-sets/<source-set-id>/extraction/`.
- Do not persist raw PDFs as durable case artifacts unless the product
  retention policy explicitly changes.
- Quote filenames with spaces when running a single-file command.

Examples:

```bash
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api --api-key "<issued-tax-server-key>" --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction
uv run --python .venv/bin/python --no-project -m src.process_pdfs_via_api --api-key "<issued-tax-server-key>" --input-dir workspace/cases/case-001/sessions/session-001/source-pdfs --output-dir workspace/cases/case-001/source-sets/source-set-001/extraction --disable-mistral-fallback
```
