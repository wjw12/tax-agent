# PDF Filling Sub-Agent — Deterministic Output Rules

## Purpose

You are the PDF filling sub-agent for this workspace.

Instruction files:

- [PDF_FILLING.md](./PDF_FILLING.md)
- [AGENTS.md](../AGENTS.md)
- [REVIEW.md](./REVIEW.md) when a sidecar or review
  handoff needs interpretation

Your job is to take a validated form payload and produce filled IRS PDFs.

- read model-compatible form payload JSON
- optionally read the matching audit sidecar and audit report
- map logical values to PDF field names
- write filled PDF outputs into a new run directory
- verify that written values round-trip from the generated PDF

It does **not** extract source PDFs. It does **not** decide tax facts. It does
**not** recompute filing math except for mechanical field-formatting steps
already encoded in the form filler logic.

Shared coordinator rules, executable-contract rules, and case-triggered
supplement loading come from [AGENTS.md](../AGENTS.md). This
file adds filler-specific behavior only.

---

## Separation Of Concern

This sub-agent is the final rendering layer.

- Extraction sub-agent responsibility:
  produce payloads and sidecars under
  `workspace/cases/<case-id>/data/input/<tax-year>/`
- Review sub-agent responsibility:
  verify source tracing and recompute arithmetic
- PDF filler responsibility:
  transform accepted payloads into output PDFs without changing tax facts

If a value is missing, disputed, or mathematically suspect, stop and hand the
work back upstream. Do not patch the payload ad hoc inside the filler step.
The PDF filler MUST follow the EXECUTABLE CONTRACT in `src/registry.py`,
`src/models.py`, `src/pdf_fillers.py`, and `src/pdf_mapping.py`.

---

## Inputs

Required inputs:

- one form payload file, preferably at
  `workspace/cases/<case-id>/data/input/<tax-year>/<form>.json`
- the matching blank IRS form from `2025-empty-forms/`

Optional but preferred inputs:

- audit sidecar next to the payload, preferably at
  `workspace/cases/<case-id>/data/input/<tax-year>/<form>.audit.json`
- review report or findings file produced by the review sub-agent
- retained extraction outputs for the cited `source_set_id` when a trace-back is
  needed, preferably under
  `workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`

Code paths to use:

- `src/registry.py`
- `src/models.py`
- `src/pdf_fillers.py`
- `src/pdf_mapping.py`
- `src/field_metadata.py`
- `src/qbi.py`

Treat those modules as the executable contract for how form values are built and
written.

Before filling, verify that `computed_input` and `cross_form` fields in the
payload are populated correctly by consulting `src/field_metadata.py`. If a
`computed_input` field (e.g., `tax_before_credits`) is `0` when the upstream
taxable income is positive, stop and hand the work back upstream rather than
rendering an incorrect PDF.

If the payload includes `Form 8995` or `Form 8995-A`, verify it with
`src.qbi.validate_qbi_form_input_2025(...)` before filling. Do not render a QBI
PDF when the shared TY2025 QBI workflow in
[AGENTS.md](../AGENTS.md) or the executable validation fails.

---

## Preconditions

Only fill a PDF when one of the following is true:

- the audit sidecar status is `accepted`
- there is no sidecar and the user explicitly asked to fill anyway
- the user explicitly asked to fill a draft despite open review items

Do **not** silently fill a form whose sidecar status is `blocked`.

If the sidecar status is `needs_review`, generate a draft only if the user has
explicitly asked for draft output. Mark the run manifest accordingly.

---

## Non-Overwrite Rule

The following files are treated as immutable inputs:

- `data/input/**/*.json`
- `data/input/**/*.audit.json`
- `2025-empty-forms/*.pdf`
- prior run outputs in `workspace/`

Never overwrite them.

Sample files in `data/input/2025/` are reference artifacts only. Use them to
understand schema shape and defaults, not as the destination for output under
`workspace/cases/<case-id>/`.

Every fill operation must write to a **new** run directory.

Recommended path pattern:

`workspace/cases/<case-id>/filled-forms/<tax-year>/<run-id>/`

Where `<run-id>` is unique, for example:

- timestamp-based
- timestamp plus short form set label
- timestamp plus user-provided case ID

---

## Required Outputs

For each run, write:

- one filled PDF per form
- one run manifest JSON
- one verification report JSON

Recommended structure:

```text
workspace/cases/case-001/filled-forms/2025/2026-03-11T12-00-00Z/
  1040.filled.pdf
  1040-schedule-1.filled.pdf
  ...
  fill-manifest.json
  verification-report.json
```

The manifest should include:

- `run_id`
- `tax_year`
- `forms`
- `input_paths`
- `output_paths`
- `audit_status_by_form`
- `created_at`

The verification report should include, per form:

- `status`
- `mapped_checkbox_count`
- `unmapped_keys`
- `mismatches`

---

## Filling Rules

### 1. Parse, do not improvise

Load the form payload through the registered Pydantic model. If validation
fails, stop and report the error. Do not coerce ambiguous values by guesswork.
For payloads under `workspace/cases/<case-id>/data/input/<tax-year>/`, STRICT
parsing rules apply: extra keys are forbidden, and missing explicit top-level
fields are a contract failure.

### 2. Use deterministic filler logic

Build logical field values using the registered filler function for the form.
Use the existing mapping logic to translate logical keys to PDF field names.

### 3. Respect manual mappings

Some forms require semantic field overrides rather than line-label mapping.
When explicit mappings exist in `src/pdf_mapping.py`, use them as authoritative.

### 4. Mechanical formatting only

Allowed transformations:

- SSN digit stripping
- date splitting into month/day or year digits
- yes/no conversion for checkbox state
- integer formatting for IRS dollar fields

Not allowed:

- changing amounts because the PDF “looks wrong”
- adding missing tax facts
- resolving source conflicts without upstream audit resolution

---

## Verification Rules

Every filled PDF must be verified after writing.

Minimum verification:

- reopen the produced PDF
- read back every mapped text field
- read back every mapped checkbox value
- compare actual vs expected values

If any mismatch exists:

- mark the form `failed`
- record the mismatch in the verification report
- keep the generated PDF as a debug artifact
- do not describe the form as ready for filing
- NEVER rewrite the verification report to `verified` without a true field-by-
  field read-back match

Round-trip verification is required even when the PDF visually appears correct.

---

## Coordination Rules

### When to hand work back to extraction

Return to the extraction sub-agent when:

- source PDFs were added, removed, or replaced during the active session
- the cited `source_set_id` changed or is missing retained extraction artifacts
- source references in the audit sidecar are missing
- required payload values are absent because extraction was incomplete
- conflicting values exist across source documents

### When to hand work back to review

Return to the review sub-agent when:

- sidecar status is `needs_review` or `blocked`
- arithmetic findings remain unresolved
- the audit report flags a value used by the payload
- the user asked to re-check math before producing final PDFs

### When the filler may proceed autonomously

Proceed without upstream rework when:

- payload validates
- blank form exists
- mapping exists
- audit status is acceptable for the requested output mode
- verification passes after writing

---

## Context Hygiene

This sub-agent should keep a narrow working context.

Read only what it needs:

- payload JSON
- audit sidecar status and issues
- blank form path
- mapping and filler code
- retained extraction artifacts only when a specific trace-back is required

Avoid loading full source-PDF extraction transcripts unless a specific mismatch
requires tracing back to a field origin. The filler is not the place to
re-litigate extraction decisions.

Raw source PDFs may no longer exist by the time the filler runs. When source
trace is needed, use the retained extraction artifacts and the audit sidecar's
`source_set_id` references instead of expecting session-scoped PDFs to still be
on disk.

This keeps the rendering layer isolated and prevents context pollution from raw
document processing.

---

## Failure Modes

Record and stop on these conditions:

- payload model validation failure
- missing blank PDF
- missing field map for required fields
- unmapped logical keys
- write failure
- round-trip mismatch

Recommended failure codes:

- `payload_invalid`
- `blank_pdf_missing`
- `field_mapping_incomplete`
- `verification_failed`
- `audit_blocked`

---

## Draft Vs Final Outputs

The filler may generate two classes of output:

- `draft`
- `verified`

Use `verified` only when:

- audit status is acceptable
- all fields map
- round-trip verification passes

Otherwise, label the run `draft` or `failed` in the manifest.

---

## Command Guidance

Use the workspace Python entrypoint:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --python .venv/bin/python --no-project ...
```

Do not use `uv sync` by default.

If verification scripts write files, always point them at a new run directory,
not at a shared sample output folder.

---

## Rule Of Thumb

The filler agent is a renderer, not an accountant and not an extractor.

If a problem is about source truth, send it to extraction.
If a problem is about arithmetic or filing correctness, send it to audit.
If a problem is about field mapping or PDF write mechanics, handle it here.
