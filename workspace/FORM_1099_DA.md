# Form 1099-DA — Operational Notes

## What Form 1099-DA Means

Form 1099-DA is a digital asset disposition reporting form.

For tax year 2025, broker reporting on `Form 1099-DA` begins for transactions
on or after `2025-01-01`.
Treat the form primarily as a proceeds-reporting document.
Do not treat it as a complete gain or loss statement by itself.

Key rule:

- gross proceeds is not taxable gain

Gross proceeds reflects the total amount received from dispositions. It can be
large even when the actual taxable gain is small.

## 2025 Return Mapping Rule

For tax year 2025, digital-asset transactions use the new `Form 8949` box
codes:

- `G/H/I` for short-term transactions
- `J/K/L` for long-term transactions

Do not use the legacy `C` or `F` boxes for digital-asset transactions.

Use:

- `G` or `J` when `Form 1099-DA` was issued and basis was reported to the IRS
- `H` or `K` when `Form 1099-DA` was issued but basis was not reported or not
  provided
- `I` or `L` when there is no `Form 1099-DA`

## What Counts As a Disposition

For tax reporting purposes, dispositions can include:

- digital asset to digital asset exchanges
- digital asset to fiat sales
- other transactions where value is received from selling or exchanging a digital asset

Do not assume a reported amount reflects a cash withdrawal. It may reflect many
small exchanges or swaps.

## Cost Basis Rule For 2025

For tax year 2025, Form 1099-DA may show proceeds without complete cost basis.

If cost basis is missing, incomplete, or unclear:

- do not assume basis
- do not assume gain equals proceeds
- ask the taxpayer for their cost basis records or transaction history
- ask where the asset was originally acquired and whether it was transferred in from elsewhere

Acceptable follow-up questions include:

- Do you have your transaction history or tax export showing what you paid for these assets?
- Were these assets bought in the same account where they were sold, or transferred in from another platform or wallet?
- Do you already have a gain/loss report or cost basis report for these transactions?

If the taxpayer can provide records, the case may still be supportable.
If the taxpayer cannot provide enough records to support basis, then the case
may become unsupported because the filing position would not be defensible.

If a customer transferred assets in from another platform, transfer statements
may help with lot ordering, but they are not a substitute for defensible basis
support on the return.

## Covered Vs Non-Covered

If a disposition is marked non-covered, do not assume cost basis was reported
to the IRS.

Non-covered generally means the taxpayer may need their own records to support
basis and holding period.

## Missing Form Rule

Do not treat "I did not receive a Form 1099-DA" as a reason to skip reporting.

For tax year 2025, foreign brokers may not furnish `Form 1099-DA`.
Taxable digital-asset transactions still must be reported whether or not the
taxpayer received the form.

## Time Zone Note

Digital asset reporting on Form 1099-DA may use Eastern Time for trade timing.

If the taxpayer is asking why a trade appears in one tax year instead of the
next, consider that a trade shortly after midnight in another time zone may
still fall into a different tax year under the form's reporting convention.

## Wash Sale Note

Do not apply stock wash sale assumptions to digital assets by default.

## Customer-Facing Guidance

When speaking to taxpayers:

- explain that the form shows total sale/exchange amounts, not necessarily taxable profit
- avoid technical language unless needed
- if basis is missing, ask for records plainly instead of declaring the case unsupported too early
- focus on what records are needed next

Bad:

- "Your proceeds are high so this likely exceeds scope."
- "This requires basis reconstruction."

Better:

- "This form shows the total amount moved through sales and exchanges, not your actual profit. I still need the cost information for those assets."
- "To finish this accurately, I need the records showing what you originally paid for the assets you sold or swapped."

## Source Pointers

Load only if needed:

- [broker-reporting-faq.md](./broker-reporting-faq.md)
- [understanding-1099da.md](./understanding-1099da.md)
