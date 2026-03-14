"""Per-form deterministic processors built on typed JSON inputs."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from .core import FormComputation, sum_decimals, to_decimal
from .models import (
    Form1040Input,
    Form1040NRScheduleAInput,
    Form1040NRScheduleNECInput,
    Form1040NRScheduleOIInput,
    Form1040NRInput,
    Form1040SRInput,
    Schedule1AInput,
    Form2441Input,
    Form4562Input,
    Form8862Input,
    Form8863Input,
    Form8889Input,
    Form8949Input,
    Form8962Input,
    Form8995AInput,
    Form8995Input,
    Form8829Input,
    Schedule1Input,
    Schedule2Input,
    Schedule3Input,
    Schedule8812Input,
    ScheduleAInput,
    ScheduleBInput,
    ScheduleCInput,
    ScheduleDInput,
    ScheduleEICInput,
    ScheduleEInput,
    ScheduleSEInput,
)


def _sum_named_amounts(items) -> Decimal:
    return sum_decimals(item.amount for item in items)


def _thousands_floor(value: Decimal) -> Decimal:
    return (value / Decimal("1000")).to_integral_value(rounding=ROUND_FLOOR)


def _thousands_ceiling(value: Decimal) -> Decimal:
    return (value / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING)


def process_1040(data: Form1040Input) -> FormComputation:
    deduction = max(data.standard_deduction, data.itemized_deductions)
    total_income = (
        data.wages
        + data.taxable_interest
        + data.ordinary_dividends
        + data.taxable_ira_distributions
        + data.taxable_pension_annuity_income
        + data.taxable_social_security_benefits
        + data.capital_gain_or_loss
        + data.schedule_1_additional_income
    )
    agi = total_income - data.schedule_1_adjustments
    taxable_income_before_qbi = max(Decimal("0"), agi - deduction)
    taxable_income = max(Decimal("0"), taxable_income_before_qbi - data.qbi_deduction)
    total_tax = max(Decimal("0"), data.tax_before_credits - data.nonrefundable_credits) + data.other_taxes
    total_payments = (
        data.federal_withholding
        + data.estimated_tax_payments
        + data.refundable_credits
        + data.amount_applied_from_prior_year
    )
    refund_or_amount_owed = total_payments - total_tax

    form = FormComputation(form_code=data.form_code, form_name=f"Form {data.form_code}")
    form.metadata.update(
        {
            "filing_status": data.filing_status,
            "taxpayer_name": f"{data.taxpayer.first_name} {data.taxpayer.last_name}",
            "dependent_count": len(data.dependents),
            "digital_assets": data.digital_assets,
        }
    )
    form.add_line("1a", "Wages, salaries, tips", data.wages)
    form.add_line("2b", "Taxable interest", data.taxable_interest)
    form.add_line("3a", "Qualified dividends", data.qualified_dividends)
    form.add_line("3b", "Ordinary dividends", data.ordinary_dividends)
    form.add_line("4a", "IRA distributions", data.ira_distributions)
    form.add_line("4b", "Taxable IRA distributions", data.taxable_ira_distributions)
    form.add_line("5a", "Pensions and annuities", data.pension_annuity_income)
    form.add_line("5b", "Taxable pensions and annuities", data.taxable_pension_annuity_income)
    form.add_line("6a", "Social security benefits", data.social_security_benefits)
    form.add_line("6b", "Taxable social security benefits", data.taxable_social_security_benefits)
    form.add_line("7", "Capital gain or loss", data.capital_gain_or_loss)
    form.add_line("8", "Other income from Schedule 1", data.schedule_1_additional_income)
    form.add_line("9", "Total income", total_income, formula="1a+2b+3b+4b+5b+6b+7+8")
    form.add_line("10", "Adjustments to income", data.schedule_1_adjustments)
    form.add_line("11", "Adjusted gross income", agi, formula="9-10")
    form.add_line("12", "Standard or itemized deduction", deduction)
    form.add_line("13", "Qualified business income deduction", data.qbi_deduction)
    form.add_line("15", "Taxable income", taxable_income, formula="max(0,11-12-13)")
    form.add_line("16", "Tax", data.tax_before_credits)
    form.add_line("19", "Nonrefundable credits", data.nonrefundable_credits)
    form.add_line("23", "Other taxes", data.other_taxes)
    form.add_line("24", "Total tax", total_tax, formula="max(0,16-19)+23")
    form.add_line("25d", "Federal income tax withheld", data.federal_withholding)
    form.add_line("26", "Estimated tax payments", data.estimated_tax_payments)
    form.add_line("28", "Refundable credits", data.refundable_credits)
    form.add_line("31", "Amount applied from prior year", data.amount_applied_from_prior_year)
    form.add_line("33", "Total payments", total_payments, formula="25d+26+28+31")
    form.add_line("34", "Refund", max(Decimal("0"), refund_or_amount_owed))
    form.add_line("37", "Amount you owe", max(Decimal("0"), -refund_or_amount_owed))
    return form


def process_1040_sr(data: Form1040SRInput) -> FormComputation:
    result = process_1040(data)
    result.form_code = "1040-SR"
    result.form_name = "Form 1040-SR"
    return result


def process_1040_nr(data: Form1040NRInput) -> FormComputation:
    effectively_connected_income = (
        data.wages
        + data.taxable_interest
        + data.ordinary_dividends
        + data.taxable_ira_distributions
        + data.taxable_pension_annuity_income
        + data.capital_gain_or_loss
        + data.schedule_1_additional_income
    )
    adjusted_gross_income = effectively_connected_income - data.schedule_1_adjustments
    total_deductions = (
        max(data.itemized_deductions, data.standard_deduction)
        + data.qbi_deduction
        + data.estate_or_trust_exemption
        + data.schedule_1a_additional_deductions
    )
    taxable_income = max(Decimal("0"), adjusted_gross_income - total_deductions)
    tax_before_credits = data.tax_before_credits + data.schedule_2_additional_taxes
    total_credits = (
        data.child_tax_credit_or_other_dependent_credit + data.schedule_3_nonrefundable_credits
    )
    tax_after_credits = max(Decimal("0"), tax_before_credits - total_credits)
    total_other_taxes = data.nec_tax + data.other_taxes + data.transportation_tax
    total_tax = tax_after_credits + total_other_taxes
    withholding_total = data.withholding_w2 + data.withholding_1099 + data.withholding_other_forms
    total_other_payments = (
        data.additional_child_tax_credit
        + data.form_1040c_credit
        + data.refundable_adoption_credit
        + data.schedule_3_refundable_credits
    )
    total_payments = (
        withholding_total
        + data.withholding_8805
        + data.withholding_8288a
        + data.withholding_1042s
        + data.estimated_tax_payments
        + total_other_payments
    )
    overpayment = max(Decimal("0"), total_payments - total_tax)
    amount_owed = max(Decimal("0"), total_tax - total_payments)

    form = FormComputation(form_code=data.form_code, form_name="Form 1040-NR")
    form.metadata.update(
        {
            "filing_status": data.filing_status,
            "taxpayer_name": f"{data.taxpayer.first_name} {data.taxpayer.last_name}",
            "dependent_count": len(data.dependents),
            "digital_assets": data.digital_assets,
            "country_of_citizenship": data.country_of_citizenship or "",
            "country_of_tax_residence": data.country_of_tax_residence or "",
            "visa_type": data.visa_type or "",
            "days_present_in_us": data.days_present_in_us or 0,
            "claims_treaty_benefits": data.claims_treaty_benefits,
            "treaty_country": data.treaty_country or "",
            "has_dual_status": data.has_dual_status,
        }
    )
    form.add_line("1a", "Wages, salaries, tips, etc.", data.wages)
    form.add_line("1k", "Total income exempt by treaty from Schedule OI", data.treaty_exempt_income)
    form.add_line("1z", "Add lines 1a through 1h", data.wages, formula="1a")
    form.add_line("2b", "Taxable interest", data.taxable_interest)
    form.add_line("3a", "Qualified dividends", data.qualified_dividends)
    form.add_line("3b", "Ordinary dividends", data.ordinary_dividends)
    form.add_line("4a", "IRA distributions", data.ira_distributions)
    form.add_line("4b", "Taxable IRA distributions", data.taxable_ira_distributions)
    form.add_line("5a", "Pensions and annuities", data.pension_annuity_income)
    form.add_line("5b", "Taxable pensions and annuities", data.taxable_pension_annuity_income)
    form.add_line("7a", "Capital gain or loss", data.capital_gain_or_loss)
    form.add_line("8", "Other income from Schedule 1", data.schedule_1_additional_income)
    form.add_line(
        "9",
        "Total effectively connected income",
        effectively_connected_income,
        formula="1a+2b+3b+4b+5b+7a+8",
    )
    form.add_line("11a", "Adjustments to income", data.schedule_1_adjustments)
    form.add_line("11b", "Adjusted gross income", adjusted_gross_income, formula="9-11a")
    form.add_line("12", "Itemized or standard deduction", max(data.itemized_deductions, data.standard_deduction))
    form.add_line("13a", "Qualified business income deduction", data.qbi_deduction)
    form.add_line("13b", "Estate or trust exemption", data.estate_or_trust_exemption)
    form.add_line("13c", "Additional deductions from Schedule 1-A", data.schedule_1a_additional_deductions)
    form.add_line("14", "Total deductions", total_deductions, formula="12+13a+13b+13c")
    form.add_line("15", "Taxable income", taxable_income, formula="max(0,11b-14)")
    form.add_line("16", "Tax", data.tax_before_credits)
    form.add_line("17", "Additional taxes from Schedule 2", data.schedule_2_additional_taxes)
    form.add_line("18", "Tax before credits", tax_before_credits, formula="16+17")
    form.add_line(
        "19",
        "Child tax credit or credit for other dependents",
        data.child_tax_credit_or_other_dependent_credit,
    )
    form.add_line("20", "Nonrefundable credits from Schedule 3", data.schedule_3_nonrefundable_credits)
    form.add_line("21", "Total credits", total_credits, formula="19+20")
    form.add_line("22", "Tax after credits", tax_after_credits, formula="max(0,18-21)")
    form.add_line("23a", "Tax on income not effectively connected with a U.S. trade or business", data.nec_tax)
    form.add_line("23b", "Other taxes", data.other_taxes)
    form.add_line("23c", "Transportation tax", data.transportation_tax)
    form.add_line("23d", "Total other taxes", total_other_taxes, formula="23a+23b+23c")
    form.add_line("24", "Total tax", total_tax, formula="22+23d")
    form.add_line("25a", "Federal income tax withheld from Forms W-2", data.withholding_w2)
    form.add_line("25b", "Federal income tax withheld from Forms 1099", data.withholding_1099)
    form.add_line("25c", "Federal income tax withheld from other forms", data.withholding_other_forms)
    form.add_line("25d", "Total withholding from Forms W-2, 1099, and other forms", withholding_total, formula="25a+25b+25c")
    form.add_line("25e", "Federal income tax withheld from Forms 8805", data.withholding_8805)
    form.add_line("25f", "Federal income tax withheld from Forms 8288-A", data.withholding_8288a)
    form.add_line("25g", "Federal income tax withheld from Forms 1042-S", data.withholding_1042s)
    form.add_line("26", "Estimated tax payments and amount applied from 2024 return", data.estimated_tax_payments)
    form.add_line("28", "Additional child tax credit", data.additional_child_tax_credit)
    form.add_line("29", "Credit for amount paid with Form 1040-C", data.form_1040c_credit)
    form.add_line("30", "Refundable adoption credit", data.refundable_adoption_credit)
    form.add_line("31", "Refundable credits from Schedule 3", data.schedule_3_refundable_credits)
    form.add_line("32", "Total other payments and refundable credits", total_other_payments, formula="28+29+30+31")
    form.add_line("33", "Total payments", total_payments, formula="25d+25e+25f+25g+26+32")
    form.add_line("34", "Overpayment", overpayment, formula="max(0,33-24)")
    form.add_line("35a", "Refund amount", max(Decimal("0"), overpayment - data.amount_applied_to_next_year))
    form.add_line("36", "Amount applied to 2026 estimated tax", data.amount_applied_to_next_year)
    form.add_line("37", "Amount you owe", amount_owed, formula="max(0,24-33)")
    form.add_line("38", "Estimated tax penalty", Decimal("0"))
    return form


def process_1040_nr_schedule_oi(data: Form1040NRScheduleOIInput) -> FormComputation:
    form = FormComputation(form_code=data.form_code, form_name="Schedule OI (Form 1040-NR)")
    treaty_total = sum_decimals(claim.current_year_exempt_income for claim in data.treaty_claims)
    form.metadata.update(
        {
            "return_name": data.return_name,
            "return_identifying_number": data.return_identifying_number,
            "citizenship_countries": data.citizenship_countries,
            "tax_residence_country": data.tax_residence_country,
            "visa_type": data.visa_type,
            "entry_exit_count": len(data.entry_departure_dates),
            "treaty_claim_count": len(data.treaty_claims),
        }
    )
    form.add_line("l1e", "Total treaty-exempt income", treaty_total)
    return form


def process_1040_nr_schedule_a(data: Form1040NRScheduleAInput) -> FormComputation:
    state_tax_cap = Decimal("20000") if data.filing_status == "married_filing_separately" else Decimal("40000")
    deductible_state_taxes = min(data.state_local_income_taxes, state_tax_cap)
    charity_total = (
        data.gifts_by_cash_or_check
        + data.other_than_cash_or_check_gifts
        + data.charitable_carryover_from_prior_year
    )
    total_itemized = (
        deductible_state_taxes
        + charity_total
        + data.casualty_and_theft_losses
        + data.other_itemized_deduction_amount
    )
    form = FormComputation(form_code=data.form_code, form_name="Schedule A (Form 1040-NR)")
    form.metadata["other_itemized_deduction_description"] = data.other_itemized_deduction_description
    form.add_line("1a", "State and local income taxes", data.state_local_income_taxes)
    form.add_line("1b", "Deductible state and local income taxes", deductible_state_taxes)
    form.add_line("2", "Gifts by cash or check", data.gifts_by_cash_or_check)
    form.add_line("3", "Other than by cash or check", data.other_than_cash_or_check_gifts)
    form.add_line("4", "Carryover from prior year", data.charitable_carryover_from_prior_year)
    form.add_line("5", "Total charitable contributions", charity_total, formula="2+3+4")
    form.add_line("6", "Casualty and theft losses", data.casualty_and_theft_losses)
    form.add_line("7", "Other itemized deductions", data.other_itemized_deduction_amount)
    form.add_line("8", "Total itemized deductions", total_itemized, formula="1b+5+6+7")
    return form


def process_schedule_1_a(data: Schedule1AInput) -> FormComputation:
    jointly = data.filing_status == "married_filing_jointly"
    modified_agi_adjustments = (
        data.excluded_income_puerto_rico
        + data.form_2555_line_45
        + data.form_2555_line_50
        + data.form_4563_line_15
    )
    line_3 = data.modified_agi_base + modified_agi_adjustments
    line_4c = max(data.qualified_tips_w2, data.qualified_tips_form_4137)
    line_6 = line_4c + data.qualified_tips_trade_or_business
    line_7 = min(line_6, Decimal("25000"))
    line_9 = Decimal("300000") if jointly else Decimal("150000")
    line_10 = max(Decimal("0"), line_3 - line_9)
    line_11 = _thousands_floor(line_10) if line_10 > 0 else Decimal("0")
    line_12 = line_11 * Decimal("100")
    line_13 = max(Decimal("0"), line_7 - line_12)

    line_14c = data.qualified_overtime_w2 + data.qualified_overtime_1099
    line_15 = min(line_14c, Decimal("25000") if jointly else Decimal("12500"))
    line_17 = Decimal("300000") if jointly else Decimal("150000")
    line_18 = max(Decimal("0"), line_3 - line_17)
    line_19 = _thousands_floor(line_18) if line_18 > 0 else Decimal("0")
    line_20 = line_19 * Decimal("100")
    line_21 = max(Decimal("0"), line_15 - line_20)

    entry_one = data.vehicle_loan_interest_entries[0] if data.vehicle_loan_interest_entries else None
    entry_two = data.vehicle_loan_interest_entries[1] if len(data.vehicle_loan_interest_entries) > 1 else None
    line_23 = sum_decimals(entry.interest_for_schedule_1a for entry in data.vehicle_loan_interest_entries[:2])
    line_24 = min(line_23, Decimal("10000"))
    line_26 = Decimal("200000") if jointly else Decimal("100000")
    line_27 = max(Decimal("0"), line_3 - line_26)
    line_28 = _thousands_ceiling(line_27) if line_27 > 0 else Decimal("0")
    line_29 = line_28 * Decimal("200")
    line_30 = line_24 if line_27 <= 0 else max(Decimal("0"), line_24 - line_29)

    line_32 = Decimal("150000") if jointly else Decimal("75000")
    line_33 = max(Decimal("0"), line_3 - line_32)
    line_34 = line_33 * Decimal("0.06")
    line_35 = max(Decimal("0"), Decimal("6000") - line_34)
    line_36a = line_35 if data.taxpayer_is_eligible_senior else Decimal("0")
    line_36b = line_35 if jointly and data.spouse_is_eligible_senior else Decimal("0")
    line_37 = line_36a + line_36b
    line_38 = line_13 + line_21 + line_30 + line_37

    form = FormComputation(form_code=data.form_code, form_name="Schedule 1-A (Form 1040)")
    form.metadata.update(
        {
            "return_name": data.return_name,
            "return_identifying_number": data.return_identifying_number,
            "filing_status": data.filing_status,
            "vehicle_1_vin": entry_one.vin if entry_one else "",
            "vehicle_2_vin": entry_two.vin if entry_two else "",
        }
    )
    form.add_line("1", "Amount from Form 1040, 1040-SR, or 1040-NR line 11b", data.modified_agi_base)
    form.add_line("2a", "Excluded Puerto Rico income", data.excluded_income_puerto_rico)
    form.add_line("2b", "Form 2555 line 45", data.form_2555_line_45)
    form.add_line("2c", "Form 2555 line 50", data.form_2555_line_50)
    form.add_line("2d", "Form 4563 line 15", data.form_4563_line_15)
    form.add_line("2e", "Total MAGI adjustments", modified_agi_adjustments, formula="2a+2b+2c+2d")
    form.add_line("3", "Modified adjusted gross income", line_3, formula="1+2e")
    form.add_line("4a", "Qualified tips from Form W-2", data.qualified_tips_w2)
    form.add_line("4b", "Qualified tips from Form 4137", data.qualified_tips_form_4137)
    form.add_line("4c", "Qualified employee tips used for deduction", line_4c, formula="max(4a,4b)")
    form.add_line("5", "Qualified tips from trade or business", data.qualified_tips_trade_or_business)
    form.add_line("6", "Total qualified tips", line_6, formula="4c+5")
    form.add_line("7", "Tip deduction cap", line_7)
    form.add_line("8", "Amount from line 3", line_3)
    form.add_line("9", "MAGI threshold for tip deduction", line_9)
    form.add_line("10", "Excess MAGI over threshold", line_10, formula="max(0,8-9)")
    form.add_line("11", "Thousands of excess MAGI", line_11)
    form.add_line("12", "MAGI phaseout amount", line_12, formula="11*100")
    form.add_line("13", "Qualified tips deduction", line_13, formula="max(0,7-12)")
    form.add_line("14c", "Total qualified overtime compensation", line_14c, formula="14a+14b")
    form.add_line("15", "Overtime deduction cap", line_15)
    form.add_line("16", "Amount from line 3", line_3)
    form.add_line("17", "MAGI threshold for overtime deduction", line_17)
    form.add_line("18", "Excess MAGI over threshold", line_18, formula="max(0,16-17)")
    form.add_line("19", "Thousands of excess MAGI", line_19)
    form.add_line("20", "MAGI phaseout amount", line_20, formula="19*100")
    form.add_line("21", "Qualified overtime compensation deduction", line_21, formula="max(0,15-20)")
    form.add_line("23", "Qualified passenger vehicle loan interest", line_23)
    form.add_line("24", "Qualified passenger vehicle loan interest cap", line_24)
    form.add_line("25", "Amount from line 3", line_3)
    form.add_line("26", "MAGI threshold for car loan interest deduction", line_26)
    form.add_line("27", "Excess MAGI over threshold", line_27, formula="max(0,25-26)")
    form.add_line("28", "Thousands of excess MAGI rounded up", line_28)
    form.add_line("29", "MAGI phaseout amount", line_29, formula="28*200")
    form.add_line("30", "Qualified passenger vehicle loan interest deduction", line_30)
    form.add_line("31", "Amount from line 3", line_3)
    form.add_line("32", "MAGI threshold for enhanced senior deduction", line_32)
    form.add_line("33", "Excess MAGI over threshold", line_33, formula="max(0,31-32)")
    form.add_line("34", "Senior deduction phaseout amount", line_34, formula="33*0.06")
    form.add_line("35", "Base enhanced senior deduction amount", line_35)
    form.add_line("36a", "Taxpayer enhanced senior deduction", line_36a)
    form.add_line("36b", "Spouse enhanced senior deduction", line_36b)
    form.add_line("37", "Enhanced deduction for seniors", line_37, formula="36a+36b")
    form.add_line("38", "Total additional deductions", line_38, formula="13+21+30+37")
    return form


def process_schedule_1(data: Schedule1Input) -> FormComputation:
    additional_income = _sum_named_amounts(data.additional_income_items)
    adjustments = _sum_named_amounts(data.adjustment_items)
    form = FormComputation(form_code=data.form_code, form_name="Schedule 1")
    form.metadata["additional_income_descriptions"] = [item.description for item in data.additional_income_items]
    form.metadata["adjustment_descriptions"] = [item.description for item in data.adjustment_items]
    form.add_line("10", "Additional income total", additional_income)
    form.add_line("26", "Adjustments total", adjustments)
    return form


def process_1040_nr_schedule_nec(data: Form1040NRScheduleNECInput) -> FormComputation:
    capital_loss = Decimal("0")
    capital_gain = Decimal("0")
    for tx in data.capital_transactions[:5]:
        delta = tx.proceeds - tx.cost_basis
        if delta >= 0:
            capital_gain += delta
        else:
            capital_loss += -delta
    line_18 = max(Decimal("0"), capital_gain - capital_loss)

    total_10 = sum_decimals(row.amount_at_10_percent for row in data.income_rows)
    total_15 = sum_decimals(row.amount_at_15_percent for row in data.income_rows)
    total_30 = sum_decimals(row.amount_at_30_percent for row in data.income_rows)
    total_other = sum_decimals(row.amount_at_other_rate for row in data.income_rows)
    if data.capital_gain_rate_class == "10":
        total_10 += line_18
    elif data.capital_gain_rate_class == "15":
        total_15 += line_18
    elif data.capital_gain_rate_class == "30":
        total_30 += line_18
    else:
        total_other += line_18

    tax_10 = total_10 * Decimal("0.10")
    tax_15 = total_15 * Decimal("0.15")
    tax_30 = total_30 * Decimal("0.30")
    tax_other = total_other * (data.other_rate_percent / Decimal("100"))
    line_15 = tax_10 + tax_15 + tax_30 + tax_other

    form = FormComputation(form_code=data.form_code, form_name="Schedule NEC (Form 1040-NR)")
    form.metadata.update(
        {
            "return_name": data.return_name,
            "return_identifying_number": data.return_identifying_number,
            "other_rate_percent": str(data.other_rate_percent),
            "income_row_count": len(data.income_rows),
            "capital_transaction_count": len(data.capital_transactions),
            "capital_gain_rate_class": data.capital_gain_rate_class,
        }
    )
    form.add_line("13a", "Total income taxed at 10%", total_10)
    form.add_line("13b", "Total income taxed at 15%", total_15)
    form.add_line("13c", "Total income taxed at 30%", total_30)
    form.add_line("13d", "Total income taxed at other rate", total_other)
    form.add_line("14a", "Tax on 10% income", tax_10)
    form.add_line("14b", "Tax on 15% income", tax_15)
    form.add_line("14c", "Tax on 30% income", tax_30)
    form.add_line("14d", "Tax on other-rate income", tax_other)
    form.add_line("15", "Tax on income not effectively connected with a U.S. trade or business", line_15)
    form.add_line("17f", "Capital transaction losses", capital_loss)
    form.add_line("17g", "Capital transaction gains", capital_gain)
    form.add_line("18", "Net capital gain", line_18)
    return form


def process_schedule_2(data: Schedule2Input) -> FormComputation:
    total = _sum_named_amounts(data.additional_tax_items)
    form = FormComputation(form_code=data.form_code, form_name="Schedule 2")
    form.metadata["tax_items"] = [item.description for item in data.additional_tax_items]
    form.add_line("21", "Total additional taxes", total)
    return form


def process_schedule_3(data: Schedule3Input) -> FormComputation:
    nonrefundable = _sum_named_amounts(data.nonrefundable_credit_items)
    payments = _sum_named_amounts(data.payment_items)
    form = FormComputation(form_code=data.form_code, form_name="Schedule 3")
    form.metadata["credit_items"] = [item.description for item in data.nonrefundable_credit_items]
    form.metadata["payment_items"] = [item.description for item in data.payment_items]
    form.add_line("8", "Nonrefundable credits total", nonrefundable)
    form.add_line("15", "Other payments and refundable credits total", payments)
    return form


def process_schedule_a(data: ScheduleAInput) -> FormComputation:
    medical_floor = data.agi * Decimal("0.075")
    deductible_medical = max(Decimal("0"), data.unreimbursed_medical_expenses - medical_floor)
    taxes_before_cap = max(data.state_local_income_taxes, data.state_local_sales_taxes)
    total_taxes = min(
        data.salt_cap,
        taxes_before_cap + data.real_estate_taxes + data.personal_property_taxes + data.other_taxes,
    )
    interest_total = (
        data.mortgage_interest
        + data.points_not_reported_on_form_1098
        + data.mortgage_insurance_premiums
        + data.investment_interest
    )
    charity_total = data.gifts_to_charity_cash + data.gifts_to_charity_other
    total_itemized = (
        deductible_medical
        + total_taxes
        + interest_total
        + charity_total
        + data.casualty_and_theft_losses
        + data.other_itemized_deductions
    )
    form = FormComputation(form_code=data.form_code, form_name="Schedule A")
    form.add_line("4", "Medical and dental expenses deduction", deductible_medical)
    form.add_line("5e", "Taxes you paid", total_taxes)
    form.add_line("8e", "Interest paid", interest_total)
    form.add_line("12", "Gifts to charity", charity_total)
    form.add_line("15", "Casualty and theft losses", data.casualty_and_theft_losses)
    form.add_line("16", "Other itemized deductions", data.other_itemized_deductions)
    form.add_line("17", "Total itemized deductions", total_itemized)
    return form


def process_schedule_b(data: ScheduleBInput) -> FormComputation:
    interest_total = _sum_named_amounts(data.interest_income)
    dividends_total = _sum_named_amounts(data.ordinary_dividends)
    form = FormComputation(form_code=data.form_code, form_name="Schedule B")
    form.metadata["interest_payers"] = [item.payer for item in data.interest_income]
    form.metadata["dividend_payers"] = [item.payer for item in data.ordinary_dividends]
    form.metadata["foreign_accounts"] = data.foreign_accounts
    form.metadata["foreign_trust"] = data.foreign_trust
    form.add_line("2", "Taxable interest", interest_total)
    form.add_line("6", "Ordinary dividends", dividends_total)
    return form


def process_schedule_d(data: ScheduleDInput) -> FormComputation:
    short_term = _sum_named_amounts(data.short_term_totals) + data.short_term_carryover
    long_term = _sum_named_amounts(data.long_term_totals) + data.long_term_carryover
    combined = short_term + long_term
    deductible_loss = min(Decimal("3000"), abs(combined)) if combined < 0 else Decimal("0")
    form = FormComputation(form_code=data.form_code, form_name="Schedule D")
    form.add_line("7", "Net short-term capital gain or loss", short_term)
    form.add_line("15", "Net long-term capital gain or loss", long_term)
    form.add_line("16", "Combined net capital gain or loss", combined)
    form.add_line("21", "Capital loss deduction", deductible_loss)
    return form


def process_8949(data: Form8949Input) -> FormComputation:
    short_proceeds = Decimal("0")
    short_basis = Decimal("0")
    short_adjustments = Decimal("0")
    short_gain = Decimal("0")
    long_proceeds = Decimal("0")
    long_basis = Decimal("0")
    long_adjustments = Decimal("0")
    long_gain = Decimal("0")
    for tx in data.transactions:
        if tx.term == "short":
            short_proceeds += tx.proceeds
            short_basis += tx.cost_basis
            short_adjustments += tx.adjustment_amount
            short_gain += tx.gain_or_loss
        else:
            long_proceeds += tx.proceeds
            long_basis += tx.cost_basis
            long_adjustments += tx.adjustment_amount
            long_gain += tx.gain_or_loss
    form = FormComputation(form_code=data.form_code, form_name="Form 8949")
    form.metadata["transaction_count"] = len(data.transactions)
    form.add_line("short_proceeds", "Short-term proceeds", short_proceeds)
    form.add_line("short_basis", "Short-term basis", short_basis)
    form.add_line("short_adjustments", "Short-term adjustments", short_adjustments)
    form.add_line("short_gain", "Short-term gain or loss", short_gain)
    form.add_line("long_proceeds", "Long-term proceeds", long_proceeds)
    form.add_line("long_basis", "Long-term basis", long_basis)
    form.add_line("long_adjustments", "Long-term adjustments", long_adjustments)
    form.add_line("long_gain", "Long-term gain or loss", long_gain)
    return form


def process_schedule_c(data: ScheduleCInput) -> FormComputation:
    gross_receipts = _sum_named_amounts(data.income_items)
    expenses = _sum_named_amounts(data.expense_items) + _sum_named_amounts(data.other_expense_items)
    net_profit = gross_receipts - expenses
    form = FormComputation(form_code=data.form_code, form_name="Schedule C")
    form.metadata["business_name"] = data.business_name
    form.metadata["principal_business_code"] = data.principal_business_code
    form.metadata["accounting_method"] = data.accounting_method
    form.add_line("1", "Gross receipts or sales", gross_receipts)
    form.add_line("7", "Gross income", gross_receipts)
    form.add_line("28", "Total expenses", expenses)
    form.add_line("31", "Net profit or loss", net_profit)
    return form


def process_schedule_se(data: ScheduleSEInput) -> FormComputation:
    earnings = max(Decimal("0"), (data.net_profit + data.optional_farm_income + data.optional_church_employee_income) * Decimal("0.9235"))
    se_tax = earnings * Decimal("0.153")
    deduction = se_tax * Decimal("0.5")
    form = FormComputation(form_code=data.form_code, form_name="Schedule SE")
    form.add_line("2", "Net profit or loss from Schedule C", data.net_profit)
    form.add_line("4c", "Net earnings from self-employment", earnings)
    form.add_line("12", "Self-employment tax", se_tax)
    form.add_line("13", "Deduction for one-half of self-employment tax", deduction)
    return form


def process_4562(data: Form4562Input) -> FormComputation:
    elected_section_179 = sum_decimals(asset.section_179_election for asset in data.assets)
    bonus_depreciation = Decimal("0")
    ordinary_depreciation = Decimal("0")
    total_basis = Decimal("0")
    for asset in data.assets:
        business_basis = asset.cost * (asset.business_use_percent / Decimal("100"))
        total_basis += business_basis
        bonus_depreciation += business_basis * (asset.bonus_depreciation_rate / Decimal("100"))
        if asset.recovery_period_years > 0:
            ordinary_depreciation += max(Decimal("0"), business_basis - asset.section_179_election) / asset.recovery_period_years
    total_depreciation = elected_section_179 + bonus_depreciation + ordinary_depreciation
    form = FormComputation(form_code=data.form_code, form_name="Form 4562")
    form.metadata["asset_count"] = len(data.assets)
    form.add_line("2", "Total cost elected for section 179", total_basis)
    form.add_line("12", "Section 179 expense deduction", elected_section_179)
    form.add_line("14", "Special depreciation allowance", bonus_depreciation)
    form.add_line("22", "Total depreciation and amortization", total_depreciation)
    return form


def process_8829(data: Form8829Input) -> FormComputation:
    business_use_pct = Decimal("0")
    if data.home_area_sqft > 0:
        business_use_pct = data.office_area_sqft / data.home_area_sqft
    direct_total = _sum_named_amounts(data.direct_expenses)
    indirect_total = _sum_named_amounts(data.indirect_expenses)
    allocable_indirect = indirect_total * business_use_pct
    tentative_deduction = direct_total + allocable_indirect + data.carryover_from_prior_year
    deduction = min(tentative_deduction, data.gross_income_limitation)
    carryover = max(Decimal("0"), tentative_deduction - deduction)
    form = FormComputation(form_code=data.form_code, form_name="Form 8829")
    form.add_line("7", "Business use percentage", business_use_pct * Decimal("100"))
    form.add_line("18", "Direct expenses", direct_total)
    form.add_line("20", "Indirect expenses allocable to business", allocable_indirect)
    form.add_line("35", "Allowable home office deduction", deduction)
    form.add_line("36", "Carryover to next year", carryover)
    return form


def process_8995(data: Form8995Input) -> FormComputation:
    qbi_total = sum_decimals(item.qualified_business_income for item in data.businesses)
    reit_ptp = sum_decimals(item.reit_ptp_income for item in data.businesses)
    qbi_component = qbi_total * Decimal("0.20")
    reit_component = reit_ptp * Decimal("0.20")
    taxable_limit_base = max(Decimal("0"), data.taxable_income_before_qbi - data.net_capital_gains)
    taxable_limit = taxable_limit_base * Decimal("0.20")
    deduction = min(qbi_component + reit_component, taxable_limit)
    form = FormComputation(form_code=data.form_code, form_name="Form 8995")
    form.metadata["businesses"] = [item.business_name for item in data.businesses]
    form.add_line("1", "Qualified business income", qbi_total)
    form.add_line("4", "20% of qualified business income", qbi_component)
    form.add_line("6", "20% of REIT/PTP income", reit_component)
    form.add_line("11", "Taxable income limitation", taxable_limit)
    form.add_line("15", "Qualified business income deduction", deduction)
    return form


def process_8995_a(data: Form8995AInput) -> FormComputation:
    total_qbi = Decimal("0")
    total_component = Decimal("0")
    for business in data.businesses:
        qbi_component = business.qualified_business_income * Decimal("0.20")
        wage_property_limit = max(
            business.w2_wages * Decimal("0.50"),
            business.w2_wages * Decimal("0.25") + business.ubia_of_qualified_property * Decimal("0.025"),
        )
        total_qbi += business.qualified_business_income
        total_component += min(qbi_component, wage_property_limit if wage_property_limit > 0 else qbi_component)
    taxable_limit_base = max(Decimal("0"), data.taxable_income_before_qbi - data.net_capital_gains)
    taxable_limit = taxable_limit_base * Decimal("0.20")
    deduction = min(total_component, taxable_limit)
    form = FormComputation(form_code=data.form_code, form_name="Form 8995-A")
    form.metadata["businesses"] = [item.business_name for item in data.businesses]
    form.add_line("1", "Qualified business income", total_qbi)
    form.add_line("7", "Combined QBI component", total_component)
    form.add_line("25", "Taxable income limitation", taxable_limit)
    form.add_line("26", "Qualified business income deduction", deduction)
    return form


def process_schedule_e(data: ScheduleEInput) -> FormComputation:
    total_income = Decimal("0")
    total_expenses = Decimal("0")
    for activity in data.rental_activities:
        total_income += _sum_named_amounts(activity.income_items)
        total_expenses += _sum_named_amounts(activity.expense_items) + activity.depreciation
    net_income = total_income - total_expenses
    form = FormComputation(form_code=data.form_code, form_name="Schedule E")
    form.metadata["properties"] = [item.property_name for item in data.rental_activities]
    form.add_line("3", "Total rents and royalties", total_income)
    form.add_line("20", "Total expenses", total_expenses)
    form.add_line("21", "Income or loss", net_income)
    return form


def process_8812(data: Schedule8812Input) -> FormComputation:
    child_count = len(data.qualifying_children)
    other_count = len(data.other_dependents)
    base_child_credit = Decimal(child_count) * data.child_tax_credit_per_child
    other_dependent_credit = Decimal(other_count) * data.credit_for_other_dependents
    total_potential_credit = base_child_credit + other_dependent_credit
    phaseout_base = max(Decimal("0"), data.modified_agi - data.phaseout_threshold)
    phaseout_units = (
        (phaseout_base / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING)
        if phaseout_base > 0
        else Decimal("0")
    )
    phaseout_reduction = phaseout_units * Decimal("50")
    allowable_nonrefundable = min(data.tax_liability_before_credits, max(Decimal("0"), total_potential_credit - phaseout_reduction))
    additional_child_credit = max(Decimal("0"), base_child_credit - allowable_nonrefundable)
    form = FormComputation(form_code=data.form_code, form_name="Schedule 8812")
    form.add_line("4", "Potential child tax credit", base_child_credit)
    form.add_line("5", "Credit for other dependents", other_dependent_credit)
    form.add_line("14", "Allowed nonrefundable child tax credit", allowable_nonrefundable)
    form.add_line("27", "Additional child tax credit", additional_child_credit)
    return form


def process_schedule_eic(data: ScheduleEICInput) -> FormComputation:
    form = FormComputation(form_code=data.form_code, form_name="Schedule EIC")
    form.metadata["filing_status"] = data.filing_status
    form.metadata["qualifying_children"] = [
        f"{child.first_name} {child.last_name}" for child in data.qualifying_children
    ]
    form.add_line("earned_income", "Earned income", data.earned_income)
    form.add_line("agi", "Adjusted gross income", data.agi)
    form.add_line("investment_income", "Investment income", data.investment_income)
    form.add_line("child_count", "Qualifying child count", Decimal(len(data.qualifying_children)))
    return form


def process_2441(data: Form2441Input) -> FormComputation:
    qualifying_expenses = sum_decimals(person.qualifying_expenses for person in data.qualifying_persons)
    expense_limit = Decimal("3000") if len(data.qualifying_persons) == 1 else Decimal("6000")
    used_expenses = min(qualifying_expenses, expense_limit)
    income_limit = min(data.taxpayer_earned_income, data.spouse_earned_income or data.taxpayer_earned_income)
    adjusted_expenses = max(Decimal("0"), min(used_expenses, income_limit) - data.dependent_care_benefits)
    applicable_percentage = max(Decimal("0.20"), Decimal("0.35") - (data.agi // Decimal("2000")) * Decimal("0.01"))
    credit = adjusted_expenses * applicable_percentage
    form = FormComputation(form_code=data.form_code, form_name="Form 2441")
    form.metadata["providers"] = [provider.name for provider in data.providers]
    form.add_line("3", "Qualified expenses", qualifying_expenses)
    form.add_line("8", "Employment-related expenses", min(used_expenses, income_limit))
    form.add_line("9", "Dependent care benefits", data.dependent_care_benefits)
    form.add_line("11", "Adjusted qualified expenses", adjusted_expenses)
    form.add_line("12", "Applicable percentage", applicable_percentage * Decimal("100"))
    form.add_line("13", "Child and dependent care credit", credit)
    return form


def process_8863(data: Form8863Input) -> FormComputation:
    aotc_credit = Decimal("0")
    llc_expenses = Decimal("0")
    for student in data.students:
        net_expenses = max(Decimal("0"), student.qualified_expenses - student.scholarships_and_grants)
        if student.credit_type == "aotc":
            first_portion = min(net_expenses, Decimal("2000"))
            second_portion = min(max(Decimal("0"), net_expenses - Decimal("2000")), Decimal("2000"))
            aotc_credit += first_portion + (second_portion * Decimal("0.25"))
        else:
            llc_expenses += net_expenses
    llc_credit = min(llc_expenses, Decimal("10000")) * Decimal("0.20")
    total_credit = aotc_credit + llc_credit
    form = FormComputation(form_code=data.form_code, form_name="Form 8863")
    form.metadata["students"] = [student.student_name for student in data.students]
    form.add_line("4", "American opportunity credit", aotc_credit)
    form.add_line("19", "Lifetime learning credit", llc_credit)
    form.add_line("30", "Total education credits", total_credit)
    return form


def process_8889(data: Form8889Input) -> FormComputation:
    annual_limit = Decimal("4300") if data.coverage_type == "self" else Decimal("8550")
    if data.age_55_or_older:
        annual_limit += Decimal("1000")
    prorated_limit = annual_limit * Decimal(data.months_eligible) / Decimal("12")
    allowed_contributions = min(
        prorated_limit,
        data.taxpayer_contributions + data.employer_contributions + data.prior_year_excess_contributions,
    )
    deduction = max(Decimal("0"), allowed_contributions - data.employer_contributions)
    taxable_distribution = max(Decimal("0"), data.distributions - data.qualified_medical_expenses)
    additional_tax = taxable_distribution * Decimal("0.20")
    form = FormComputation(form_code=data.form_code, form_name="Form 8889")
    form.add_line("2", "Taxpayer HSA contributions", data.taxpayer_contributions)
    form.add_line("5", "HSA contribution limit", prorated_limit)
    form.add_line("9", "Employer contributions", data.employer_contributions)
    form.add_line("13", "HSA deduction", deduction)
    form.add_line("14a", "Total distributions", data.distributions)
    form.add_line("15", "Qualified medical expenses", data.qualified_medical_expenses)
    form.add_line("16", "Taxable HSA distributions", taxable_distribution)
    form.add_line("17b", "Additional tax on taxable distributions", additional_tax)
    return form


def process_8962(data: Form8962Input) -> FormComputation:
    annual_household_contribution = data.household_income * data.annual_contribution_percentage
    monthly_household_contribution = annual_household_contribution / Decimal("12")
    annual_ptc = Decimal("0")
    annual_aptc = Decimal("0")
    annual_premiums = Decimal("0")
    annual_slcsp = Decimal("0")
    for month in data.monthly_entries:
        annual_premiums += month.enrollment_premiums
        annual_slcsp += month.slcsp_premiums
        annual_aptc += month.advance_payment_ptc
        monthly_ptc = max(
            Decimal("0"),
            min(month.enrollment_premiums, max(Decimal("0"), month.slcsp_premiums - monthly_household_contribution)),
        )
        annual_ptc += monthly_ptc
    net_ptc = max(Decimal("0"), annual_ptc - annual_aptc)
    excess_aptc = max(Decimal("0"), annual_aptc - annual_ptc)
    form = FormComputation(form_code=data.form_code, form_name="Form 8962")
    form.add_line("11", "Annual enrollment premiums", annual_premiums)
    form.add_line("12", "Annual SLCSP premiums", annual_slcsp)
    form.add_line("23", "Annual household contribution amount", annual_household_contribution)
    form.add_line("24", "Premium tax credit", annual_ptc)
    form.add_line("25", "Advance payment of premium tax credit", annual_aptc)
    form.add_line("26", "Net premium tax credit", net_ptc)
    form.add_line("29", "Excess advance premium tax credit repayment", excess_aptc)
    return form


def process_8862(data: Form8862Input) -> FormComputation:
    form = FormComputation(form_code=data.form_code, form_name="Form 8862")
    form.metadata["credit_type"] = data.credit_type
    form.metadata["tax_year_of_disallowance"] = data.tax_year_of_disallowance
    form.metadata["reason_disallowance_resolved"] = data.reason_disallowance_resolved
    form.metadata["qualifying_children"] = [
        f"{child.first_name} {child.last_name}" for child in data.qualifying_children
    ]
    form.add_line("child_count", "Qualifying child count", Decimal(len(data.qualifying_children)))
    return form
