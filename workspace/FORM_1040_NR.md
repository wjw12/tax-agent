# Form 1040-NR Intake Guide

Use this guide when the taxpayer is a nonresident alien for 2025 or when that
status is still being determined.

This file is the source of truth for nonresident-return scope, intake
questions, and 2025-specific rules. Do not rely on general model memory for
`1040-NR` details when this file applies.

When the case is on the `1040-NR` path, also load
[FORM_1040_NR_2025_DELTAS.md](./FORM_1040_NR_2025_DELTAS.md)
for the narrow 2025 deltas and unsupported-topic routing.

## Supported 2025 Scope

The current 2025 Form 1040-NR path is intended for straightforward individual
returns.

Supported:

- single, married filing separately, or qualifying surviving spouse filing status
- wage income, interest, dividends, capital gains, and other basic federal income items
- withholding reported on W-2, 1099, 1042-S, 8805, or 8288-A
- straightforward treaty claims only when the treaty can be confirmed as in
  force for 2025, the exempt amount can be tied to source documents or clear
  taxpayer facts, and the position does not require unsupported `Form 8833`
  handling
- Schedule OI, Schedule A (Form 1040-NR), Schedule NEC (Form 1040-NR), and
  Schedule 1-A (Form 1040) when they fit the supported scope
- standard deduction only when it is actually available, such as the limited
  cases allowed by the instructions

Important 2025 note:

- `Schedule 1-A (Form 1040)` is new for 2025.
- The 2025 `1040-NR` instructions explicitly direct `Form 1040-NR` line `13c`
  to `Schedule 1-A`, line `38`.
- Treaty-exempt compensation must not be netted out of `1040-NR` line `1a`.
  Report taxable wages on line `1a`, report treaty-exempt income on line `1k`,
  and complete `Schedule OI`, item `L`.
- If the withholding form overstates taxable wages because the payer did not
  apply the treaty correctly, the return still reports the treaty-exempt amount
  separately on line `1k` and `Schedule OI`; do not rewrite the gross wage
  field to a net amount.
- Do not rely on model memory for the 2025 `Schedule 1-A` deduction rules.
  Treat the repo code and instructions as the source of truth for the new
  tips, overtime, car-loan-interest, and senior-deduction flow.
- Nonresident aliens generally cannot claim the qualified passenger vehicle
  loan interest deduction. Do not route that deduction onto a supported
  `1040-NR` return unless the applicable 2025 instruction file says it is
  allowed.
- For 2025, the terminated U.S.-Hungary income tax treaty generally cannot
  support a treaty claim. Do not allow a Hungary treaty-based exclusion on a
  2025 `1040-NR` return unless a later official source in the case materials
  clearly overrides that.

Unsupported:

- dual-status returns
- resident election cases with a spouse
- treaty-based positions that require specialized disclosure, `Form 8833`,
  treaty interpretation beyond the case materials, or a treaty whose 2025
  status cannot be confirmed
- foreign partnership transfer cases that require Schedule P (Form 1040-NR)
- estate or trust Form 1040-NR filings
- Trump account elections that require `Form 4547`
- farmland-sale installment elections that require `Form 1062`
- 2025 adoption-credit cases that require unsupported `Form 8839` handling
- cases where substantial presence, exempt-individual days, or treaty status
  cannot be determined from taxpayer facts

## Intake Order

Ask only one or two questions at a time, but collect these facts before routing
documents:

1. Confirm the 2025 residency path.
   Ask:
   - Were you a U.S. citizen, green card holder, resident alien, nonresident alien, or dual-status taxpayer for 2025?
   - If nonresident or unsure, what visa status did you hold and roughly how many days were you present in the U.S. during 2025?

2. Confirm the filing status.
   Ask:
   - Are you single, married, or a qualifying surviving spouse for 2025?
   - If married, did your spouse have U.S. tax residency, and are you trying to make any election to file as residents?
   - If married, does your spouse have an SSN or ITIN?

3. Collect identifying and residency facts.
   Ask:
   - What identifying number will appear on the return: SSN or ITIN?
   - What is your country of citizenship and your country of tax residence?
   - What address should appear on the return?

4. Screen for unsupported nonresident complexity.
   Ask:
   - Are you claiming any treaty benefit, treaty-exempt wages, or other treaty-based exclusion?
   - Which treaty country and treaty article are you relying on, and did you claim that treaty benefit in any prior U.S. tax year?
   - Do you have a `1042-S`, treaty statement, or other document showing the exempt amount or withholding?
   - Is this a dual-status year, first-year choice year, or departure-year filing?
   - Did you sell or transfer an interest in a foreign partnership or receive anything that would require Schedule P?

5. Collect document and withholding facts.
   Ask:
   - Which forms do you have: W-2, 1042-S, 1099, 8805, 8288-A, brokerage statements, K-1s?
   - Did you have any U.S. withholding or estimated payments?
   - Did you earn income in any states?
   - Did you have non-effectively connected income, treaty disclosures, or nonresident itemized deductions that belong on Schedule NEC, Schedule OI, or Schedule A?

## Payload Fields To Capture

For the current `1040-NR` JSON path, collect at least:

- `filing_status`
- taxpayer name
- taxpayer SSN or ITIN
- taxpayer address, including foreign country if applicable
- `country_of_citizenship`
- `country_of_tax_residence`
- `visa_type`
- `days_present_in_us`
- `claims_treaty_benefits`
- `has_dual_status`
- treaty article, prior-year treaty months claimed, prior-year U.S. return filing fact, and current-year exempt income when `Schedule OI` item `L` applies
- wages, interest, dividends, retirement income, capital gain/loss, and other income
- adjustments, deductions, tax, withholding, estimated payments, and refundable credits

## Blank Forms

Use official IRS sources for the 2025 nonresident packet:

- About page: `https://www.irs.gov/forms-instructions/about-form-1040-nr`
- Blank Form 1040-NR PDF: `https://www.irs.gov/pub/irs-pdf/f1040nr.pdf`
- Instructions PDF: `https://www.irs.gov/pub/irs-pdf/i1040nr.pdf`

Depending on the case, the taxpayer may also need the schedules linked from the
IRS about page, especially Schedule OI (Form 1040-NR), Schedule A
(Form 1040-NR), Schedule NEC (Form 1040-NR), and Schedule 1-A (Form 1040).

Do not request or support Schedule P (Form 1040-NR). Treat any case that needs
Schedule P or foreign partnership transfer reporting as unsupported.
