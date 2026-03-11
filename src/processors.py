"""Per-form deterministic processors built on typed JSON inputs."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING

from .core import FormComputation, sum_decimals, to_decimal
from .models import (
    Form1040Input,
    Form1040SRInput,
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


def process_schedule_1(data: Schedule1Input) -> FormComputation:
    additional_income = _sum_named_amounts(data.additional_income_items)
    adjustments = _sum_named_amounts(data.adjustment_items)
    form = FormComputation(form_code=data.form_code, form_name="Schedule 1")
    form.metadata["additional_income_descriptions"] = [item.description for item in data.additional_income_items]
    form.metadata["adjustment_descriptions"] = [item.description for item in data.adjustment_items]
    form.add_line("10", "Additional income total", additional_income)
    form.add_line("26", "Adjustments total", adjustments)
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
