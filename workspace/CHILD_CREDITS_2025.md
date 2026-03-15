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

- The child must have a valid `SSN` issued on or before the return due date,
  including extensions.
- If the child does not meet the `CTC` or `ACTC` `SSN` rule, consider `ODC`
  instead of forcing `CTC` or `ACTC`.
- On a joint return for tax year 2025, one spouse must have a valid `SSN` to
  claim `CTC` or `ACTC`.
- The other spouse must have either an `SSN` or `ITIN` issued on or before the
  return due date, including extensions.

## ODC And AOTC

- `ODC` and `AOTC` have different `TIN` rules from `CTC` and `ACTC`.
- Do not reuse the `CTC` or `ACTC` `SSN` rule for `ODC` or `AOTC`.

## Form 8862 Recovery Rule

- If the taxpayer is reclaiming a previously disallowed credit, apply the 2025
  identity rules together with the `Form 8862` re-claim rules.
- Do not assume an older-year identity pattern still works for a 2025 reclaim.

## Amount Rule

Use the repo's form logic and supported forms for current-year dollar amounts.
Do not carry the `CTC` or `ACTC` amount constants in this prompt.

## Source Pointers

- [instructions-8862.md](/home/appuser/tax/workspace/instructions-8862.md)
- [i1040gi-whatsnew.md](/home/appuser/tax/workspace/i1040gi-whatsnew.md)
