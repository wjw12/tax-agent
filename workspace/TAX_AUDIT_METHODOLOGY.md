# Tax Audit Methodology — Supported Return Verification

## Purpose

This document defines the audit procedure for this tax workspace.

It is not a tax law primer. The model already knows general tax concepts. This
document exists to enforce the workflow discipline that makes this agent system
reliable:

- trace filed values back to saved evidence
- recompute derived figures independently
- reconcile values across forms and schedules
- distinguish critical blockers from non-critical open items
- return a clear status and next handoff for the coordinator

Use this procedure for supported individual returns in this workspace, not just
brokerage summaries or 1099 cases.

---

## Review Sub-Agent In The System

The review sub-agent sits after extraction and before PDF filling.

Its job is narrow:

- read extracted form payloads and audit sidecars from the active case folder
- verify source traceability
- verify arithmetic and internal consistency
- verify cross-form continuity for the supported return
- classify issues as `accepted`, `needs_review`, or `blocked`

It does not:

- extract source PDFs from scratch
- decide new tax facts without evidence
- silently fix missing basis or missing substantiation
- fill PDFs
- keep re-asking for the same non-critical missing item after the taxpayer has
  explicitly approved moving forward without it

If a gap is non-critical and the taxpayer has clearly authorized proceeding,
record the open item, keep the status conservative, and move the case forward.
Do not trap the workflow in a repetitive question loop.

---

## Audit Loop

```text
INVENTORY case -> TRACE inputs -> RECOMPUTE math -> RECONCILE flows ->
ASSESS supportability -> REPORT status
```

Do not skip phases. Do not accept a number because it looks plausible. Do not
stop at the first mismatch; complete the pass and return the full set of
findings.

---

## Inputs

Primary inputs:

- extracted payload JSON under
  `workspace/cases/<case-id>/data/input/<tax-year>/`
- matching `.audit.json` sidecars
- retained extraction outputs under
  `workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`
- source-set manifests under
  `workspace/cases/<case-id>/source-sets/<source-set-id>/manifest.json`
- prior audit findings for the same live case when present

Optional session input when still available:

- raw source PDFs in
  `workspace/cases/<case-id>/sessions/<session-id>/source-pdfs/`

Conditional input:

- load `FORM_1099_DA.md` only when the case includes digital asset disposition
  reporting or Form 1099-DA

Read only what is needed for the form or issue being audited. Use progressive
disclosure:

- start with the target form payload and its sidecar
- pull only the retained extracted pages needed for the questioned values
- consult raw PDFs only when they are still available and a specific mismatch
  requires it
- load a specialized supplement only when the case facts trigger it

Return summaries, findings, and citations. Do not forward raw extraction dumps,
OCR chatter, or long shell logs unless a specific mismatch requires it.

---

## Phase 1 — Inventory The Case

Before checking numbers, build a compact case inventory:

- which forms and schedules were extracted
- which source documents are present in the active source-set manifest
- which supported income categories appear to be in scope
- which forms are expected but missing based on the source set or taxpayer facts
- which items are direct inputs versus derived values

The audit should test completeness, not just correctness. A mathematically
correct return can still be incomplete if a source document listed in the
source-set manifest never made it into the extracted payload set.

At this point, classify missing items into two buckets:

- `critical`: the return cannot be defended or materially changes without it
- `non-critical`: the gap should be recorded, but the case can proceed if the
  taxpayer wants to continue with that limitation understood

Examples of usually critical gaps:

- missing basis for a reported sale or exchange
- conflicting taxpayer identity or tax year across core forms
- a source document with material income that is absent from the return payload
- unresolved withholding or payment amounts used on the return

Examples of often non-critical gaps:

- a nonessential supplemental page that does not change the filed number
- descriptive detail that supports a narrative note but not a computation
- a document requested for extra comfort where the taxpayer has already
  confirmed the filing position and accepted drafting limitations

Materiality still matters. Use judgment conservatively.

---

## Phase 2 — Establish The Evidence Hierarchy

Source evidence is not equally reliable. Use a consistent hierarchy:

**Tier 1 — native digital extraction**
Use persisted clean text-layer extraction when the page had a reliable native
text layer.

**Tier 2 — OCR extraction**
Use persisted OCR output only when the text layer was garbled, missing, or
unusable. OCR values carry extra verification burden.

**Tier 3 — comparison or adjudication output**
Use side-by-side comparisons or alternate extractors only to resolve a specific
dispute. Do not treat them as the primary source when a better source exists.

Rule:

- use the highest-confidence source available for each figure
- note the source tier when judgment was required
- if two sources disagree, treat that as a finding rather than averaging or
  guessing

After raw PDF purge, the persisted extraction artifacts plus the source-set
manifest are the retained source of truth for this workflow.

---

## Phase 3 — Trace Inputs Back To Evidence

For each input value used by the return, confirm:

1. Label match
   The adjacent label supports the value the payload claims.

2. Taxpayer/document match
   The value belongs to the correct taxpayer, spouse, payer, account, property,
   business, or activity.

3. Period/tax-year match
   The value belongs to the correct tax year and reporting period.

4. Repetition/cross-check match
   If the same value appears elsewhere in the same document set, the copies
   agree. If they do not, record a finding.

5. Detail-to-total support
   When a total is supported by detail lines, independently sum the underlying
   items instead of trusting the printed subtotal.

This is the default procedure for all supported case families. Apply the same
discipline whether the source is a W-2, a broker statement, a 1099-DA, a
Schedule C ledger, or a rental statement.

---

## Phase 4 — Recompute Derived Values

Use `decimal.Decimal` for money. Do not use float arithmetic.

```python
from decimal import Decimal

def d(value):
    return Decimal(str(value))
```

For every derived figure in the payload or audit sidecar:

- identify the exact upstream inputs used
- recompute the result independently
- compare computed value to reported value
- record the delta when they differ

Common derived figures include:

- subtotals and net amounts
- withholding totals
- proceeds less basis less adjustments
- Schedule C or Schedule E net results
- carryovers or allocations already computed upstream
- totals flowing from schedules into Form 1040 or related forms

Do not stop after one failure. Clusters of related failures often indicate a
systemic extraction or mapping issue rather than a one-off typo.

---

## Phase 5 — Reconcile Cross-Form Flows

Source tracing inside one form is not enough. Audit the continuity of values
across the supported return.

Examples of cross-form ties that should agree when applicable:

- wage and withholding amounts from W-2 inputs into the return totals
- interest and dividends from source forms into Schedule B or directly into the
  return flow
- capital gain or loss items into Form 8949, Schedule D, and Form 1040 flow
- Schedule C net profit into Schedule 1 and self-employment tax calculations
- Schedule E net rental results into the return flow
- estimated payments, withholding, and credits into total payments

The exact line references are form-specific and model-specific. The review
does not need generic tax education here; it needs to verify that extracted
payloads agree with each other and with the final filed flow.

If a value is internally correct on one schedule but fails downstream to the
next form, that is still an audit finding.

---

## Phase 6 — Apply Case-Family Procedures

Use targeted checks only when the case facts trigger them. Do not load every
specialized procedure by default.

### Wage And Information Return Cases

Focus on:

- taxpayer identity and tax year
- box-to-payload traceability
- withholding tie-outs
- duplicates or superseding forms

### Investment Income And Securities Disposition Cases

Focus on:

- proceeds, basis, wash-sale or adjustment fields, and holding-period character
- detail-to-total agreement when transactions roll into subtotals
- supplemental or endnote pages when they affect character, allocation, or lot
  treatment
- completeness of all payer statements in the case

Do not treat a statement cover page as the complete story when supporting pages
change how an amount is characterized or allocated.

### Digital Asset Cases

Load `FORM_1099_DA.md` when triggered.

Focus on:

- whether the source set supports proceeds, basis, and holding-period facts
- whether basis is missing, incomplete, or contradicted
- whether activity reflects sales, swaps, transfers, rewards, staking, mining,
  or other categories that need different handling

Key system rule:

- if proceeds are present but basis is missing or unclear, do not infer gain
  from proceeds; record the missing basis issue and request taxpayer records

### Schedule C Cases

Focus on:

- gross receipts completeness
- expense substantiation status
- duplicates across statements, ledgers, and payment-platform reports
- mixed personal/business use flags
- missing records that make the net result undefensible

### Schedule E Rental Cases

Focus on:

- property identity and ownership consistency
- rent totals and major expense categories
- repairs versus improvements only when the distinction is material to the
  extracted treatment
- unsupported complexity triggers already defined in `AGENTS.md`

### Credits, Payments, And Adjustments

Focus on:

- required support documents are present when the return relies on them
- credit or payment amounts tie into the return totals
- missing support is classified as critical or non-critical, not ignored

---

## Phase 7 — Sanity Checks

Run these independently of direct source tracing:

- magnitude: values are plausible for the activity and account/property/business
- sign: reductions, losses, and adjustments have the correct sign treatment
- completeness: every material source document in the case folder is represented
  somewhere in the extracted payload set
- duplication: the same income, withholding, or expense is not counted twice
- identity: taxpayer, spouse, payer, and account/property/business references
  are consistent enough for a defensible filing position

When the case facts imply a simple reasonableness ratio or implied price check,
run it. This is especially useful for sale proceeds, quantity-based
transactions, and periodic-income streams.

---

## Escalation And Loop-Avoidance Rules

Not every issue should stop the workflow, but every issue must be classified.

### `blocked`

Use when a material source, arithmetic, or supportability issue prevents a
defensible filing position. Examples:

- material income source missing from the return
- basis missing for a material disposition and the taxpayer cannot support it
- unresolved identity, tax-year, or source conflict
- arithmetic failure that changes filed results materially
- unsupported-scope issue under `AGENTS.md`

### `needs_review`

Use when the form or return is substantially built but open items remain.

This status should stop filing-ready output by default, but it does not require
the system to keep asking the same question forever. If the missing item is
non-critical and the taxpayer has explicitly approved proceeding, record that
fact and move forward with a draft or review-pending workflow.

### `accepted`

Use only when source tracing is adequate, arithmetic checks pass, and no
material unresolved issue remains for the form or return.

### Re-ask discipline

Do not repeatedly ask for the same missing document or fact when all of the
following are true:

- the item has already been requested clearly
- the user has said they do not have it or wants to proceed without it
- the gap is non-critical to a defensible draft or review-pending output

Instead:

- record the limitation
- keep the status conservative
- recommend the next handoff

If new conflicting evidence appears later, reopen the issue once with the new
reason.

---

## Reporting Contract

Every review result should produce concise outputs that the coordinator and
other sub-agents can use without replaying the whole investigation.

Required outputs:

- findings
- recomputation results
- status per form: `accepted`, `needs_review`, or `blocked`
- return-level overall status when multiple forms interact materially
- recommended next handoff

Recommended report sections:

1. Coverage and completeness
2. Source-trace findings
3. Arithmetic and cross-form reconciliation findings
4. Open items and whether they are critical or non-critical
5. Status and next handoff

Recommended live-case output locations:

- `workspace/cases/<case-id>/audit/`
- `workspace/cases/<case-id>/data/input/<tax-year>/<form>.audit.json`

Recommended retained evidence locations:

- `workspace/cases/<case-id>/source-sets/<source-set-id>/manifest.json`
- `workspace/cases/<case-id>/source-sets/<source-set-id>/extraction/`

Prefer concise, evidence-linked summaries over raw exploration dumps.

---

## Quick Checklist

```text
[ ] Case inventory built: forms present, sources present, expected items checked
[ ] Missing items classified as critical vs non-critical
[ ] Highest-confidence evidence source used for each questioned figure
[ ] Inputs traced by label, entity, year, cross-check, and detail support
[ ] Derived values recomputed with decimal.Decimal
[ ] Cross-form flows reconciled where applicable
[ ] Case-family checks applied only for triggered issues
[ ] Completeness, duplication, sign, and magnitude checks run
[ ] Re-ask discipline followed; no repetitive loop on non-critical gaps
[ ] Findings, statuses, and next handoff written for coordinator use
```
