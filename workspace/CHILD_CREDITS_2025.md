# Child Credits And Form 8862 — 2025 Identity Rules

Use this file when the case may involve:

- `CTC`
- `ACTC`
- `ODC`
- `AOTC`
- `Form 8862`
- a dependent-credit identity or timing issue

## Core 2025 Rule

Do not rely on older `CTC` or `ACTC` identity patterns.
For tax year 2025, identity timing changed and it can change the credit result.

## CTC And ACTC

- For tax year 2025, the maximum `CTC` is `2,200` dollars per qualifying
  child.
- For tax year 2025, the maximum `ACTC` is `1,700` dollars per qualifying
  child.
- The child must have a valid `SSN` issued on or before the return due date,
  including extensions.
- If the child does not meet the `CTC` or `ACTC` `SSN` rule, consider `ODC`
  instead of forcing `CTC` or `ACTC`.
- On a joint return for tax year 2025, one spouse must have a valid `SSN` to
  claim `CTC` or `ACTC`.
- The other spouse must have either an `SSN` or `ITIN` issued on or before the
  return due date, including extensions.
- Use the 2025 `CTC` and `ODC` phaseout thresholds:
  `400,000` dollars for `MFJ` and `200,000` dollars for all other filing
  statuses.

## ODC And AOTC

- Keep `ODC` at `500` dollars per dependent for tax year 2025.
- `ODC` and `AOTC` have different `TIN` rules from `CTC` and `ACTC`.
- Do not reuse the `CTC` or `ACTC` `SSN` rule for `ODC` or `AOTC`.

## Form 8862 Recovery Rule

- If the taxpayer is reclaiming a previously disallowed credit, apply the 2025
  identity rules together with the `Form 8862` re-claim rules.
- Do not assume an older-year identity pattern still works for a 2025 reclaim.

## Constants Source

Use [tax_constants_2025.py](../src/tax_constants_2025.py) as
the structured source of truth for 2025 child-credit amounts and thresholds.

## Source Pointers

- [instructions-8862.md](./instructions-8862.md)
- [i1040gi-whatsnew.md](./i1040gi-whatsnew.md)
