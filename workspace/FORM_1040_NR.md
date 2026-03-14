# Form 1040-NR Intake Guide

Use this guide when the taxpayer is a nonresident alien for 2025 or when that
status is still being determined.

## Supported 2025 Scope

The current 2025 Form 1040-NR path is intended for straightforward individual
returns.

Supported:

- single, married filing separately, or qualifying surviving spouse filing status
- wage income, interest, dividends, capital gains, and other basic federal income items
- withholding reported on W-2, 1099, 1042-S, 8805, or 8288-A
- Schedule OI, Schedule A (Form 1040-NR), Schedule NEC (Form 1040-NR), and
  Schedule 1-A (Form 1040) when they fit the supported scope
- standard deduction only when it is actually available, such as the limited
  cases allowed by the instructions

Unsupported:

- dual-status returns
- resident election cases with a spouse
- treaty-based positions that need specialized disclosure or Form 8833 support
- foreign partnership transfer cases that require Schedule P (Form 1040-NR)
- estate or trust Form 1040-NR filings
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

3. Collect identifying and residency facts.
   Ask:
   - What identifying number will appear on the return: SSN or ITIN?
   - What is your country of citizenship and your country of tax residence?
   - What address should appear on the return?

4. Screen for unsupported nonresident complexity.
   Ask:
   - Are you claiming any treaty benefit, treaty-exempt wages, or other treaty-based exclusion?
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
