# Tax Agent Handoff For API Server Integration

## Purpose

This document explains the system boundary between the API server and the tax
agent workspace in this repository.

The intended audience is the developer operating the API server and worker
daemons. The goal is to make ownership, inputs, outputs, and failure semantics
unambiguous so the API layer can treat the tax agent as a clean execution
backend rather than a conversational black box.

This document is intentionally about procedure and integration boundaries. It
does not restate generic tax knowledge.

---

## One-Sentence Model

The API server is the system of record; the tax agent worker is a bounded job
executor that reads a case package, produces tax artifacts plus summarized
status, persists durable case artifacts, and then discards raw PDFs and scratch
workspace state when the active session or job ends.

---

## System Boundary

### API server owns

- user auth, authorization, and case ownership
- job creation, scheduling, cancellation, and retries
- canonical job state in DB
- browser-facing SSE and final user-visible status
- upload orchestration to GCS and artifact metadata
- durable retention policy
- deciding when a user has explicitly approved proceeding despite non-critical
  missing items
- mapping a user action into a worker job request

### Worker daemon owns

- creating a temp session or job workspace for raw PDFs and scratch files
- downloading the case package from GCS
- running local Codex and local ACP in that temp workspace
- local coordination among extractor, auditor, reconciler, deduction reviewer,
  and PDF filler when needed
- emitting sanitized progress callbacks
- uploading durable outputs to GCS
- deleting temp files in `finally`

### Tax agent code in this repo owns

- supported-form schemas and validation in [src/models.py](/home/appuser/tax/src/models.py)
- audit sidecar schema in [src/audit_models.py](/home/appuser/tax/src/audit_models.py)
- supported form registry in [src/registry.py](/home/appuser/tax/src/registry.py)
- extraction, audit, reconciliation, deduction-review, and PDF-filling
  procedure docs in [AGENTS.md](/home/appuser/tax/AGENTS.md) and
  [workspace/](/home/appuser/tax/workspace)
- deterministic PDF field building and verification

### Explicit non-goals for the tax agent worker

- it is not the source of truth for job state
- it is not the source of truth for long-term case storage
- it should not expose raw ACP transcripts as durable product output
- it should not talk directly to browsers
- it should not invent tax facts to fill missing data
- it should not silently treat a review-pending case as filing-ready

---

## Execution Model

For v1, one submitted API job should map to one worker run.

Inside that worker run, the tax agent may use local sub-agents, but that is an
internal implementation detail. The API server should treat the worker as a
single execution unit with one overall status and one output manifest.

The recommended internal execution order is:

1. intake and scope check from provided case facts and documents
2. extraction from source PDFs into typed payload JSON plus audit sidecars
3. deduction review when expense substantiation is materially relevant
4. audit of source tracing, arithmetic, and supportability
5. reconciliation across forms and source sets when multiple artifacts interact
6. PDF filling only for accepted outputs, or draft output when explicitly allowed

The worker may stop early if the case is unsupported or materially blocked.

---

## What The API Server Must Send In

The worker request should contain only what is needed to execute a single run.

Minimum fields:

- `job_id`
- `case_id`
- `job_type`
- `input_urls`
- `output_upload_prefix`
- `callback_base_url`

Recommended fields for this tax agent:

- `instructions`
  A short coordinator instruction, not a full transcript dump.
- `case_facts_json`
  Structured intake facts already known at the API layer.
- `user_approvals_json`
  Explicit approvals that matter to loop-avoidance and draft behavior.
- `output_mode`
  `final` or `draft`
- `tax_year`
- `requested_forms`
  Optional. Useful when the API already knows the desired subset.

### Important approval field

To avoid repeated loops on non-critical missing items, the API layer should
pass explicit user intent when available, for example:

```json
{
  "proceed_without_noncritical_docs": true,
  "allow_draft_if_review_pending": true
}
```

The worker should treat this as permission to proceed conservatively. It should
still mark the case `needs_review` or `blocked` when appropriate, but it should
not keep re-asking for the same non-critical item.

---

## What The Worker Must Materialize Locally

The worker should create a fresh job directory, for example:

```text
/srv/codex/jobs/<job_id>/
  repo/
  workspace/cases/<case-id>/
    active.json
    sessions/<session-id>/
      source-pdfs/
    source-sets/<source-set-id>/
      manifest.json
      extraction/
    data/input/<tax-year>/
    audit/
    filled-forms/<tax-year>/<run-id>/
```

Within the repo, the live case contract from [AGENTS.md](/home/appuser/tax/AGENTS.md)
should be preserved:

- raw source PDFs under
  `workspace/cases/<case-id>/sessions/<session-id>/source-pdfs/`
- retained extraction JSON under
  `workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`
- extracted payloads under `workspace/cases/<case-id>/data/input/<tax-year>/`
- audit reports under `workspace/cases/<case-id>/audit/`
- filled PDFs under `workspace/cases/<case-id>/filled-forms/<tax-year>/<run-id>/`

The worker must not overwrite reference inputs under `data/input/2025/` or
blank forms under `2025-empty-forms/`.

---

## Durable Outputs The API Server Should Expect

The worker should upload only durable, user-meaningful artifacts plus machine
readable manifests.

### Primary durable outputs

- source-set manifests
- retained extraction JSON
- extracted form payload JSON files
- matching `.audit.json` sidecars
- audit report summaries
- reconciliation findings, when run
- deduction review findings, when run
- filled PDFs, when produced
- fill manifest and verification report
- one top-level run manifest for the job

### Ephemeral outputs that should stay local

- raw ACP session history
- shell command logs
- exploratory notes
- OCR scratch files unless explicitly retained for debugging
- temp copies of source documents after upload is complete
- raw PDFs after the active session lease ends

---

## Output Contract

The API server should treat the worker result as a package with two layers:

### 1. Artifact layer

Files uploaded to GCS, including:

- `workspace/cases/<case-id>/data/input/<tax-year>/<form>.json`
- `workspace/cases/<case-id>/data/input/<tax-year>/<form>.audit.json`
- `workspace/cases/<case-id>/audit/*.json` or `*.md`
- `workspace/cases/<case-id>/filled-forms/<tax-year>/<run-id>/*`

### 2. Summary layer

A compact machine-readable completion payload, for example:

```json
{
  "job_id": "job_123",
  "case_id": "case_001",
  "job_status": "done",
  "return_status": "needs_review",
  "output_mode": "draft",
  "artifacts": {
    "payloads": [".../1040.json", ".../8949.json"],
    "audit_sidecars": [".../1040.audit.json", ".../8949.audit.json"],
    "reports": [".../audit/summary.json"],
    "filled_forms": [".../filled-forms/2025/run-1/1040.filled.pdf"]
  },
  "summary": {
    "supported": true,
    "critical_open_items": [],
    "noncritical_open_items": [
      "Broker supplemental allocation page not provided; draft proceeds with limitation recorded."
    ],
    "next_handoff": "user_review"
  }
}
```

The API server should persist this summary in DB and use it to drive user
presentation. It should not parse raw transcripts to infer outcome.

---

## Status Semantics

There are two related but different status layers:

### Job status

Owned by the API server:

- `queued`
- `running`
- `done`
- `failed`
- `cancelled`

### Tax-return readiness status

Returned by the worker:

- `accepted`
- `needs_review`
- `blocked`

Interpretation:

- `accepted`
  The relevant artifacts are sufficiently supported for normal downstream use.
- `needs_review`
  The run completed, but open items remain. This can still produce a useful
  draft if the API/user requested draft behavior.
- `blocked`
  The worker found a material source, arithmetic, or supportability problem.

Important:

- a job can be `done` while the return status is `needs_review`
- a job can be `done` while some forms are produced only as draft
- only `accepted` should be treated as filing-ready by default

---

## Missing Information And User Greenlight

This repo is intentionally designed to avoid getting trapped in loops.

The API server is the right place to capture the user's explicit decision about
whether to proceed without non-critical items. The worker then uses that
decision during execution.

Recommended rule:

- if a missing item is critical, return `blocked` or at least `needs_review`
  and explain why
- if a missing item is non-critical and the user already approved proceeding,
  continue the run, record the limitation, and keep status conservative

This separation matters:

- the API server owns user consent and persistence of that consent
- the worker owns conservative execution once that consent is provided

---

## Progress Event Contract

Progress events should be sanitized and high signal. Good event types:

- `assigned`
- `started`
- `progress`
- `artifact`
- `done`
- `failed`
- `cancelled`

Good `progress.message` examples:

- `Downloaded 6 source documents`
- `Extracted payloads for 1040, Schedule B, Schedule D, and 8949`
- `Audit found 1 critical issue: missing basis support for digital asset dispositions`
- `Generated draft filled PDFs for accepted forms`

Avoid sending:

- raw OCR text
- long stack traces except in internal debug paths
- raw ACP transcript content
- taxpayer document contents in logs unless strictly needed

---

## Recommended API/Worker Contract For This Repo

### Request to worker

```json
{
  "job_id": "job_123",
  "case_id": "case_001",
  "job_type": "tax_run",
  "tax_year": 2025,
  "instructions": "Run the tax workflow for this case and return summarized findings plus durable artifacts.",
  "case_facts_json": {},
  "user_approvals_json": {
    "proceed_without_noncritical_docs": true,
    "allow_draft_if_review_pending": true
  },
  "output_mode": "draft",
  "input_urls": [
    "https://signed-gcs-url/source-1.pdf",
    "https://signed-gcs-url/source-2.pdf"
  ],
  "output_upload_prefix": "gs://bucket/jobs/job_123/",
  "callback_base_url": "https://api.internal"
}
```

### Completion callback from worker

```json
{
  "job_id": "job_123",
  "worker_id": "worker-a",
  "job_status": "done",
  "return_status": "needs_review",
  "output_mode": "draft",
  "manifest_url": "gs://bucket/jobs/job_123/run-manifest.json",
  "summary": {
    "supported": true,
    "critical_open_items": [],
    "noncritical_open_items": [
      "One nonessential support document was not provided; limitation recorded."
    ],
    "next_handoff": "user_review"
  }
}
```

---

## Practical Integration Rules

- Treat this repo as an execution engine, not as the source of durable truth.
- Persist structured manifests and summarized findings, not raw session logs.
- Pass explicit user approvals into the run request when they affect draft
  behavior or loop-avoidance.
- Keep one worker run scoped to one job in v1.
- Let the worker decide internal sub-agent usage locally.
- Use GCS as the only shared file layer between API and workers.

If these boundaries are kept clean, the API server can evolve independently
from the tax agent internals, and the tax worker can become more capable
without changing the browser contract.
