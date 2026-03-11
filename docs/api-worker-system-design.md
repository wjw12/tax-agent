# API Server / Worker System Design

This document is the implementation handoff for the fixed-worker prototype.

Audience:

- backend developer working on the control/API server
- developer working on worker-machine agent logic

The goal is to make the full system shape, boundaries, and contracts clear before the worker-side agent logic is built out.

## Design Update

This document assumes the following persistence rule:

- a user may hold a worker lease while their frontend session is active
- raw uploaded PDFs live only for the duration of that active worker session
- extracted JSON, audit sidecars, payload JSON, audit reports, and filled-form
  outputs are durable per user and per case
- once the frontend session ends and the lease expires, the worker deletes raw
  PDFs and scratch files but keeps the durable case artifacts

For this system, the retained source of truth after raw PDF purge is:

- the persisted extraction outputs for the active `source_set_id`
- the persisted form payload JSON
- the persisted `.audit.json` sidecars
- the persisted audit reports and fill verification outputs

The system does not promise that raw source PDFs remain available after the
session ends.

## Purpose

The system runs tax-processing jobs through a small control plane and a fixed set of dedicated worker VMs.

For the prototype:

- there are exactly 3 worker machines
- each worker machine runs exactly 1 active job at a time
- workers are not dynamically provisioned
- the browser never talks to ACP or to workers directly
- the API server is the only public-facing control surface
- a worker may be leased to one active user session at a time
- raw PDFs are session-scoped, not durable case artifacts

The worker developer should think of the worker as:

- one private execution service
- one local Codex/ACP environment
- one isolated session workspace for raw PDFs and scratch files
- one durable case-artifact sync target
- one callback client sending sanitized progress back to the API

## High-Level Architecture

```text
Browser
  -> API server
  -> SSE stream from API server

API server
  -> SQLite now, Postgres later if needed
  -> GCS for durable case storage
  -> private HTTP calls to fixed worker daemons

Worker daemon on each worker VM
  -> local session workspace for raw PDFs
  -> local durable-case cache
  -> local Codex CLI
  -> local codex-acp
  -> callback posts to API server
```

The API server is the source of truth for:

- session leases
- jobs
- worker assignment
- job event history
- durable case artifact metadata
- final output metadata

The worker is responsible for:

- executing the assigned job
- managing local session files
- running the local agent flow
- emitting progress events
- syncing durable case artifacts
- purging raw PDFs and scratch data when the session lease ends
- cleanup

## Why ACP Is Local to the Worker

ACP is not exposed to the browser and is not currently spoken directly by the API server.

For this prototype:

- ACP stays local to each worker VM
- the worker daemon wraps the local Codex/ACP execution
- the API server talks to the worker daemon over private HTTP

This keeps the control plane simple:

- no long-lived remote ACP transport from the API server
- no browser ACP integration
- no ACP protocol session persistence in the API layer

The worker developer can change the local ACP execution details without forcing a redesign of the API server, as long as the worker HTTP contract stays stable.

## System Components

## 1. API Server

The API server handles:

- session start or resume
- session lease renewal
- session end
- user-facing job creation
- worker scheduling
- job status reads
- SSE progress streaming
- worker callback ingestion
- cancellation requests

Main routes:

- `POST /sessions`
- `POST /sessions/{session_id}/heartbeat`
- `POST /sessions/{session_id}/end`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/events`
- `GET /jobs/{job_id}/stream`
- `POST /jobs/{job_id}/cancel`
- `GET /workers`

Internal worker callback routes:

- `POST /internal/workers/{worker_id}/heartbeat`
- `POST /internal/workers/{worker_id}/events`
- `POST /internal/workers/{worker_id}/complete`

The API also sends private requests to workers:

- `POST /run`
- `POST /cancel/{job_id}`
- `GET /health`
- `GET /status`

## 2. Worker Daemon

The worker daemon is a private service that runs on each worker VM.

It handles:

- holding at most one active session lease at a time
- accepting one job at a time within that session
- creating session workspaces and case-cache views
- downloading input files
- launching the local agent flow
- reporting progress
- uploading or exposing outputs
- deleting temporary files

Main worker routes:

- `GET /health`
- `GET /status`
- `POST /run`
- `POST /cancel/{job_id}`

The current implementation enforces one active job max per worker.

## 3. Storage

Three storage classes exist in the design:

- local worker session disk for active raw-PDF execution
- local worker cache for the active case view
- GCS for durable per-user, per-case artifacts

Current model:

- API accepts or references input files
- worker downloads inputs from `https://...` or `gs://...`
- worker materializes raw PDFs only into the active session workspace
- worker writes durable artifacts into the case store and syncs them to GCS

The worker must treat raw PDFs and scratch files as ephemeral execution
storage, not as the durable system of record.

The durable system of record is the case-artifact store for:

- source-set manifests
- extraction JSON
- form payload JSON
- audit sidecars and audit reports
- filled forms and verification manifests

### Durable Case Store

Recommended durable layout:

```text
cases/<user-id>/<case-id>/
  case.json
  active.json
  source-sets/
    <source-set-id>/
      manifest.json
      extraction/
        router.json
        extracted_raw.json
        tesseract.json
        mistral.json
        normalized-pages.json
  data/input/<tax-year>/
    <form>.json
    <form>.audit.json
  audit/
    <run-id>/
  filled-forms/<tax-year>/<run-id>/
```

Rules:

- raw PDFs do not belong in the durable case store
- extracted JSON is durable and is the retained source of truth after PDF purge
- every persisted extraction artifact should be tied to a `source_set_id`
- every downstream audit sidecar should be traceable to a `source_set_id`
- previous durable runs are immutable once written

## Fixed-Worker Model

There are exactly 3 workers.

Each worker has:

- a stable worker ID such as `worker-1`
- a stable private HTTP endpoint
- a status of `free`, `busy`, or `offline`
- at most one active job

This means the scheduler is intentionally simple:

- FIFO queue
- first free worker wins
- no autoscaling
- no multi-lane concurrency on a single VM

That is deliberate. The prototype is trying to validate:

- end-to-end job execution
- worker isolation
- streaming
- basic operational reliability

not maximize throughput yet.

## Data Model

The control plane tracks 4 main records.

### Session Leases

Fields:

- `id`
- `user_id`
- `case_id`
- `worker_id`
- `status`
- `lease_expires_at`
- `connected_at`
- `disconnected_at`
- `current_job_id`
- `created_at`
- `updated_at`

### Workers

Fields:

- `id`
- `host`
- `status`
- `current_job_id`
- `last_seen_at`

### Jobs

Fields:

- `id`
- `user_id`
- `case_id`
- `job_type`
- `status`
- `worker_id`
- `input_manifest_json`
- `output_manifest_json`
- `instructions`
- `error_text`
- `created_at`
- `updated_at`

### Job Events

Fields:

- `id`
- `job_id`
- `type`
- `message`
- `payload_json`
- `created_at`

The worker developer usually only needs to care about:

- `session_id`
- `job_id`
- `job_type`
- `instructions`
- input manifest
- event callback shape
- completion callback shape

## Session Lease Lifecycle

The intended session lifecycle is:

```text
pending -> active -> grace -> ended
pending -> active -> ended
pending -> failed
```

Recommended behavior:

1. Browser starts or resumes a case session through the API.
2. API assigns a free worker and creates a session lease.
3. API routes interactive work for that case to the leased worker.
4. While the frontend stays connected, the API renews the lease.
5. On disconnect, the session enters a short grace period.
6. If the user reconnects before expiry, resume the same worker lease.
7. If the grace period expires, the worker syncs durable artifacts, deletes raw
   PDFs and scratch files, and closes the session workspace.

The intended job lifecycle inside a session is:

```text
queued -> running -> done
queued -> running -> failed
queued -> running -> cancelled
queued -> failed
```

Worker states:

```text
free -> busy -> free
free -> offline
busy -> offline
```

Normal flow:

1. Browser starts or resumes a case session through the API.
2. API writes the session lease and assigns a free worker.
3. Browser action creates a job through the API.
4. API writes the job row and `queued` event.
5. API marks job `running`, worker `busy`, and writes `assigned`.
6. API sends `POST /run` to the leased worker.
7. Worker creates or reuses the active session workspace and starts local
   agent logic.
8. Worker sends progress callbacks to API.
9. API persists those events and fans them out via SSE.
10. Worker completes the job, syncs durable outputs if needed, and sends
    completion callback.
11. API marks the job terminal.
12. When the session lease ends, the worker purges raw PDFs and scratch files,
    then releases the worker back to `free`.

## Worker HTTP Contract

## `POST /run`

The worker receives:

```json
{
  "session_id": "sess_123",
  "job_id": "job_123",
  "user_id": "user_123",
  "case_id": "case-001",
  "job_type": "tax_run",
  "instructions": "Run the tax workspace flow on the provided inputs.",
  "case_store_prefix": "gs://bucket/cases/user_123/case-001/",
  "source_set_id": "src_2026_03_11_01",
  "input_files": [
    {"name": "input.pdf", "url": "gs://bucket/path/input.pdf"}
  ],
  "callback_base_url": "http://api.internal:8000/internal/workers/worker-1"
}
```

Worker expectations:

- reject if already busy
- create or reuse the active session workspace
- fetch inputs into the session raw-PDF area
- start local agent flow
- sync durable artifacts into the case store
- return immediately after background task launch

The HTTP response is only an acceptance signal:

```json
{"status": "accepted"}
```

## `POST /cancel/{job_id}`

The API uses this to request cancellation.

Worker expectations:

- only cancel the active job matching that `job_id`
- signal the local runner to stop
- report terminal completion through callback

## Worker Callback Contract

The worker sends three kinds of callbacks to the API.

## 1. Heartbeat

`POST {callback_base_url}/heartbeat`

Example:

```json
{
  "status": "busy",
  "current_session_id": "sess_123",
  "current_job_id": "job_123"
}
```

## 2. Progress Event

`POST {callback_base_url}/events`

Example:

```json
{
  "job_id": "job_123",
  "type": "progress",
  "message": "Running extraction and audit",
  "payload": null
}
```

Recognized event types currently include:

- `started`
- `progress`
- `artifact`

The API also uses its own event types such as `queued`, `assigned`, `done`, `failed`, and `cancelled`.

Worker progress messages should be:

- short
- sanitized
- user-safe enough to stream
- not raw ACP logs
- not raw document text

## 3. Completion

`POST {callback_base_url}/complete`

Success example:

```json
{
  "job_id": "job_123",
  "status": "done",
  "output_manifest": {
    "artifacts": [
      {"name": "summary.pdf", "uri": "gs://bucket/tax-jobs/job_123/summary.pdf"}
    ]
  },
  "error_text": null
}
```

Failure example:

```json
{
  "job_id": "job_123",
  "status": "failed",
  "output_manifest": null,
  "error_text": "Runner command exited with 1"
}
```

## Worker Filesystem Model

Recommended worker-local layout:

```text
/srv/codex/
  worker-service/
  sessions/
    <session-id>/
      source-pdfs/
      scratch/
      tmp-ocr/
  case-cache/
    <user-id>/
      <case-id>/
        active.json
        source-sets/
        data/input/
        audit/
        filled-forms/
```

The worker should create a fresh isolated raw-PDF workspace for every session
lease and a case-cache view for durable artifacts.

Expected rules:

- never mix raw PDFs between sessions
- do not mix files between users or cases
- keep raw PDFs only while the session lease is active
- persist extracted JSON and downstream artifacts into the case store
- clean up the session raw-PDF workspace after lease expiry

## Worker Agent Logic Boundary

The worker-side developer owns the logic inside the local runner.

That includes:

- how `codex-acp` is launched
- how Codex CLI is configured
- how prompts are built
- how the tax agent workflow is executed
- how local artifacts are written

That does not include:

- browser auth
- public API design
- scheduling decisions
- job queue management
- SSE fanout

The current worker process supports two runner modes:

- `mock`
- `command`

For real work, use `command`.

The command-mode wrapper receives:

- `JOB_SPEC_PATH`
- `JOB_OUTPUT_DIR`

The wrapper script should:

1. read the job spec JSON
2. run the local agent flow
3. write final outputs to `JOB_OUTPUT_DIR`
4. exit non-zero on failure

## Tax Job Interpretation

For now, the control plane treats the whole filing workflow as one job type:

- `tax_run`

That means the worker can internally perform:

- intake reasoning
- extraction
- audit
- PDF fill preparation

without the control plane splitting those into separate distributed jobs yet.

This is intentional. Stage-splitting can come later if needed.

The worker developer should assume:

- one job may run the full coordinator flow
- final outputs should be concise and durable
- intermediate chatter should stay local unless it is useful sanitized progress
- the durable case store outlives the worker session
- raw PDFs do not outlive the worker session

## Streaming Model

The browser subscribes to:

- `GET /jobs/{job_id}/stream`

This is server-sent events, not WebSockets.

The browser stream comes only from the API server.

The worker never streams directly to the browser.

The worker should think of its callbacks as:

- operational events for persistence
- UI-facing progress summaries

not as a raw log transport.

## Failure Handling

The worker should be conservative and explicit.

### Worker busy

If a worker is already busy:

- reject `POST /run` with `409`

### Local runner failure

If the local runner fails:

- send completion with `status=failed`
- include short `error_text`
- still clean up local temp workspace

### Cancellation

If cancellation is requested:

- stop the local runner if possible
- send completion with `status=cancelled`
- clean up workspace

### Worker crash

If the worker process dies:

- heartbeats stop
- API may mark worker `offline`
- assigned job may need operator review or retry

The worker developer should prefer:

- idempotent temp-dir setup
- cleanup in `finally`
- bounded logs
- no silent failure paths

## Security and Privacy Expectations

This system processes tax data, so the worker must avoid leaking sensitive content.

Required behavior:

- do not log raw tax document text
- do not send full ACP transcripts to the API by default
- do not emit secrets in progress callbacks
- keep API callback token private
- keep Codex credentials only on the worker VM
- use private network paths between API and worker
- delete raw PDFs when the session lease ends
- do not treat raw PDFs as durable system artifacts

The worker output should be limited to:

- intended job artifacts
- concise status messages
- short error descriptions

## Configuration the Worker Developer Should Expect

Common worker env vars:

- `WORKER_WORKER_ID`
- `WORKER_API_BASE_URL`
- `WORKER_CALLBACK_TOKEN`
- `WORKER_WORKSPACE_ROOT`
- `WORKER_OUTPUT_ROOT`
- `WORKER_RUNNER_MODE`
- `WORKER_RUNNER_COMMAND`
- `WORKER_GCS_PROJECT`
- `WORKER_GCS_OUTPUT_BUCKET`
- `WORKER_GCS_OUTPUT_PREFIX`
- `WORKER_CODEX_ACP_BIN`

The worker should support input URLs that are:

- `https://...`
- `gs://...`

If `WORKER_GCS_OUTPUT_BUCKET` is set, final artifacts should be uploaded and returned as `gs://...` URIs.

## Current Repo Implementation

Relevant files:

- [src/tax_server/api/app.py](/home/appuser/tax-server/src/tax_server/api/app.py)
- [src/tax_server/api/scheduler.py](/home/appuser/tax-server/src/tax_server/api/scheduler.py)
- [src/tax_server/api/transport.py](/home/appuser/tax-server/src/tax_server/api/transport.py)
- [src/tax_server/worker/app.py](/home/appuser/tax-server/src/tax_server/worker/app.py)
- [src/tax_server/worker/runner.py](/home/appuser/tax-server/src/tax_server/worker/runner.py)
- [src/tax_server/worker/artifacts.py](/home/appuser/tax-server/src/tax_server/worker/artifacts.py)
- [docs/acp-masterdoc.md](/home/appuser/tax-server/docs/acp-masterdoc.md)
- [docs/gcs-acp-setup.md](/home/appuser/tax-server/docs/gcs-acp-setup.md)

## Recommended Next Step for the Worker Developer

Implement the real command-mode runner.

That means:

1. read the job spec and session lease context
2. materialize raw PDFs into the session workspace
3. sync or mount the durable case-artifact store
4. launch local `codex-acp` + Codex CLI flow
5. run the tax agent logic
6. write durable case artifacts and final outputs
7. emit only concise progress
8. purge raw PDFs when the session lease ends
9. exit cleanly with clear failure signaling

The API server and worker daemon should remain stable while the local agent logic evolves behind that boundary.
