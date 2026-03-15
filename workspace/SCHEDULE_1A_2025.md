# Schedule 1-A (Form 1040) — 2025 Operational Rules

Use this file when the case may involve:

- qualified tips
- qualified overtime compensation
- qualified passenger vehicle loan interest
- the enhanced deduction for seniors

## Routing Rule

For tax year 2025, route these deductions to `Schedule 1-A (Form 1040)`.
Do not default them into `Schedule A`, `Schedule C`, or other schedules just
because the taxpayer itemizes or has business income.

Use the repo's form logic for caps, MAGI thresholds, and line math.
Do not rely on prompt text or general model memory for those amounts.

## Qualified Tips

- The work must be in an IRS-listed tipped occupation.
- The deduction has 2025 `SSN` and filing-status gates.
- `Forms W-2`, `1099`, and `4137` may not separately identify the deductible
  amount on 2025 forms.
- Use payer forms plus taxpayer or payroll records when reconstruction is
  needed, and document the reconstruction method.
- For nonemployee or self-employed tip cases, use only amounts supported by
  `Forms 1099` plus records.
- Self-employed tips are limited by the net income of that business.

## Qualified Overtime Compensation

- Only the `FLSA`-required overtime premium qualifies.
- Do not treat all overtime wages as deductible.
- 2025 `Forms W-2` and `1099` may not separately identify the deductible
  amount.
- Reasonable reconstruction from payroll records is allowed, but document how
  the premium amount was derived.

## Qualified Passenger Vehicle Loan Interest

- Route only the personal-use share to `Schedule 1-A`.
- If the same vehicle also has business use, only the business-use share may
  remain on `Schedule C`, `Schedule E`, or `Schedule F` if otherwise
  deductible.
- Confirm these operational gates before claiming the deduction:
  - the loan was incurred after `2024-12-31`
  - the debt is a first-lien loan
  - the vehicle is a qualifying personal-use passenger vehicle
  - the debt was originated for the taxpayer
  - the `VIN` is captured
  - the same interest is not deducted elsewhere

## Enhanced Deduction For Seniors

- Verify the age gate before claiming the deduction.
- Apply the 2025 `SSN` and joint-return conditions.
- Apply the special death-in-2025 rule when one spouse died during 2025.

## Nonresident Interaction

If the case is on the `1040-NR` path, also load
[FORM_1040_NR_2025_DELTAS.md](/home/appuser/tax/workspace/FORM_1040_NR_2025_DELTAS.md).
Nonresident aliens generally cannot claim the qualified passenger vehicle loan
interest deduction.

## Source Pointers

- [i1040gi-whatsnew.md](/home/appuser/tax/workspace/i1040gi-whatsnew.md)
