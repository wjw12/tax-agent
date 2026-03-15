"""Typed JSON input models for supported 2025 federal forms."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FederalFilingStatus = Literal[
    "single",
    "married_filing_jointly",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
]

NonresidentFilingStatus = Literal[
    "single",
    "married_filing_separately",
    "qualifying_surviving_spouse",
]


class TaxModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Address(TaxModel):
    line1: str
    line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str | None = None


class TaxpayerIdentity(TaxModel):
    first_name: str
    last_name: str
    ssn: str | None = None
    identifying_number: str | None = None
    address: Address
    date_of_birth: date | None = None
    occupation: str | None = None


class QualifyingChild(TaxModel):
    first_name: str
    last_name: str
    ssn: str
    relationship: str
    date_of_birth: date
    months_lived_with_taxpayer: int = 12
    days_lived_with_taxpayer_in_us: int | None = None
    date_of_death: date | None = None
    is_student: bool = False
    permanently_totally_disabled: bool = False


class OtherDependent(TaxModel):
    first_name: str
    last_name: str
    ssn: str
    relationship: str


class NamedAmount(TaxModel):
    description: str
    amount: Decimal


class PayerAmount(TaxModel):
    payer: str
    amount: Decimal


class CapitalTransaction(TaxModel):
    description: str
    date_acquired: date
    date_sold: date
    proceeds: Decimal
    cost_basis: Decimal
    adjustment_amount: Decimal = Decimal("0")
    adjustment_code: str | None = None
    reporting_category: Literal["A", "B", "C", "D", "E", "F"] = "A"

    @property
    def gain_or_loss(self) -> Decimal:
        return self.proceeds - self.cost_basis + self.adjustment_amount

    @property
    def term(self) -> Literal["short", "long"]:
        return "long" if (self.date_sold - self.date_acquired).days > 365 else "short"


class DepreciationAsset(TaxModel):
    description: str
    placed_in_service: date
    cost: Decimal
    business_use_percent: Decimal = Decimal("100")
    section_179_election: Decimal = Decimal("0")
    bonus_depreciation_rate: Decimal = Decimal("0")
    recovery_period_years: Decimal = Decimal("5")


class QbiBusiness(TaxModel):
    business_name: str
    qualified_business_income: Decimal
    reit_ptp_income: Decimal = Decimal("0")


class QbiComplexBusiness(TaxModel):
    business_name: str
    qualified_business_income: Decimal
    w2_wages: Decimal = Decimal("0")
    ubia_of_qualified_property: Decimal = Decimal("0")


class RentalActivity(TaxModel):
    property_name: str
    income_items: list[NamedAmount] = Field(default_factory=list)
    expense_items: list[NamedAmount] = Field(default_factory=list)
    depreciation: Decimal = Decimal("0")


class CareProvider(TaxModel):
    name: str
    tin: str
    address: Address
    amount_paid: Decimal


class CareDependent(TaxModel):
    first_name: str
    last_name: str
    ssn: str
    qualifying_expenses: Decimal


class StudentExpense(TaxModel):
    student_name: str
    student_ssn: str
    institution_name: str
    credit_type: Literal["aotc", "llc"]
    qualified_expenses: Decimal
    scholarships_and_grants: Decimal = Decimal("0")
    months_enrolled_half_time: int = 0
    completed_first_four_years: bool = False
    felony_drug_conviction: bool = False


class MonthlyMarketplaceEntry(TaxModel):
    month: Literal[
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    enrollment_premiums: Decimal
    slcsp_premiums: Decimal
    advance_payment_ptc: Decimal


class EntryExitDate(TaxModel):
    date_entered: date | None = None
    date_departed: date | None = None


class TreatyClaim(TaxModel):
    country: str
    treaty_article: str
    months_claimed_in_prior_years: int = 0
    current_year_exempt_income: Decimal = Decimal("0")


class VehicleLoanInterestEntry(TaxModel):
    vin: str
    interest_deducted_elsewhere: Decimal = Decimal("0")
    interest_for_schedule_1a: Decimal = Decimal("0")


class ScheduleNECIncomeRow(TaxModel):
    category: Literal[
        "dividends_us_corp",
        "dividends_foreign_corp",
        "dividend_equivalent",
        "interest_mortgage",
        "interest_foreign_corp",
        "interest_other",
        "industrial_royalties",
        "motion_picture_royalties",
        "other_royalties",
        "real_property_royalties",
        "pensions",
        "social_security",
        "gambling_canada",
        "gambling_other",
        "other",
    ]
    amount_at_10_percent: Decimal = Decimal("0")
    amount_at_15_percent: Decimal = Decimal("0")
    amount_at_30_percent: Decimal = Decimal("0")
    amount_at_other_rate: Decimal = Decimal("0")
    description: str | None = None
    winnings: Decimal = Decimal("0")
    losses: Decimal = Decimal("0")


class BaseFormInput(TaxModel):
    form_code: str
    tax_year: int = 2025


class Form1040Input(BaseFormInput):
    form_code: Literal["1040"] = "1040"
    filing_status: FederalFilingStatus
    taxpayer: TaxpayerIdentity
    spouse: TaxpayerIdentity | None = None
    dependents: list[QualifyingChild | OtherDependent] = Field(default_factory=list)
    digital_assets: bool = False
    wages: Decimal = Decimal("0")
    taxable_interest: Decimal = Decimal("0")
    ordinary_dividends: Decimal = Decimal("0")
    qualified_dividends: Decimal = Decimal("0")
    ira_distributions: Decimal = Decimal("0")
    taxable_ira_distributions: Decimal = Decimal("0")
    pension_annuity_income: Decimal = Decimal("0")
    taxable_pension_annuity_income: Decimal = Decimal("0")
    social_security_benefits: Decimal = Decimal("0")
    taxable_social_security_benefits: Decimal = Decimal("0")
    capital_gain_or_loss: Decimal = Decimal("0")
    schedule_1_additional_income: Decimal = Decimal("0")
    schedule_1_adjustments: Decimal = Decimal("0")
    itemized_deductions: Decimal = Decimal("0")
    standard_deduction: Decimal = Decimal("0")
    qbi_deduction: Decimal = Decimal("0")
    tax_before_credits: Decimal = Decimal("0")
    nonrefundable_credits: Decimal = Decimal("0")
    other_taxes: Decimal = Decimal("0")
    federal_withholding: Decimal = Decimal("0")
    estimated_tax_payments: Decimal = Decimal("0")
    refundable_credits: Decimal = Decimal("0")
    amount_applied_from_prior_year: Decimal = Decimal("0")


class Form1040SRInput(Form1040Input):
    form_code: Literal["1040-SR"] = "1040-SR"


class Form1040NRInput(BaseFormInput):
    form_code: Literal["1040-NR"] = "1040-NR"
    residency_status: Literal["nonresident_alien"] = "nonresident_alien"
    filing_status: NonresidentFilingStatus
    taxpayer: TaxpayerIdentity
    dependents: list[QualifyingChild | OtherDependent] = Field(default_factory=list)
    digital_assets: bool = False
    country_of_citizenship: str | None = None
    country_of_tax_residence: str | None = None
    visa_type: str | None = None
    days_present_in_us: int | None = None
    claims_treaty_benefits: bool = False
    treaty_country: str | None = None
    has_dual_status: bool = False
    qualifying_person_name: str | None = None
    wages: Decimal = Decimal("0")
    taxable_interest: Decimal = Decimal("0")
    ordinary_dividends: Decimal = Decimal("0")
    qualified_dividends: Decimal = Decimal("0")
    ira_distributions: Decimal = Decimal("0")
    taxable_ira_distributions: Decimal = Decimal("0")
    pension_annuity_income: Decimal = Decimal("0")
    taxable_pension_annuity_income: Decimal = Decimal("0")
    capital_gain_or_loss: Decimal = Decimal("0")
    schedule_1_additional_income: Decimal = Decimal("0")
    treaty_exempt_income: Decimal = Decimal("0")
    schedule_1_adjustments: Decimal = Decimal("0")
    itemized_deductions: Decimal = Decimal("0")
    standard_deduction: Decimal = Decimal("0")
    qbi_deduction: Decimal = Decimal("0")
    estate_or_trust_exemption: Decimal = Decimal("0")
    schedule_1a_additional_deductions: Decimal = Decimal("0")
    tax_before_credits: Decimal = Decimal("0")
    schedule_2_additional_taxes: Decimal = Decimal("0")
    child_tax_credit_or_other_dependent_credit: Decimal = Decimal("0")
    schedule_3_nonrefundable_credits: Decimal = Decimal("0")
    nec_tax: Decimal = Decimal("0")
    other_taxes: Decimal = Decimal("0")
    transportation_tax: Decimal = Decimal("0")
    withholding_w2: Decimal = Decimal("0")
    withholding_1099: Decimal = Decimal("0")
    withholding_other_forms: Decimal = Decimal("0")
    withholding_8805: Decimal = Decimal("0")
    withholding_8288a: Decimal = Decimal("0")
    withholding_1042s: Decimal = Decimal("0")
    estimated_tax_payments: Decimal = Decimal("0")
    additional_child_tax_credit: Decimal = Decimal("0")
    form_1040c_credit: Decimal = Decimal("0")
    refundable_adoption_credit: Decimal = Decimal("0")
    schedule_3_refundable_credits: Decimal = Decimal("0")
    amount_applied_to_next_year: Decimal = Decimal("0")


class Form1040NRScheduleOIInput(BaseFormInput):
    form_code: Literal["1040-NR-Schedule-OI"] = "1040-NR-Schedule-OI"
    return_name: str = ""
    return_identifying_number: str = ""
    citizenship_countries: str = ""
    tax_residence_country: str = ""
    visa_type: str = ""
    applied_for_green_card: bool = False
    was_us_citizen: bool = False
    was_green_card_holder: bool = False
    changed_visa_status: bool = False
    visa_status_change_details: str = ""
    entry_departure_dates: list[EntryExitDate] = Field(default_factory=list)
    commuter_from_canada: bool = False
    commuter_from_mexico: bool = False
    days_in_us_2023: int = 0
    days_in_us_2024: int = 0
    days_in_us_2025: int = 0
    previously_filed_us_return: bool = False
    prior_filing_year_and_form: str = ""
    filing_for_trust: bool = False
    trust_had_us_or_foreign_owner_or_distribution: bool = False
    received_total_compensation_over_250k: bool = False
    used_alternative_compensation_sourcing_method: bool = False
    treaty_claims: list[TreatyClaim] = Field(default_factory=list)
    taxed_on_treaty_exempt_income_in_foreign_country: bool = False
    claiming_competent_authority_benefits: bool = False
    real_property_election_first_year: bool = False
    real_property_election_continuing: bool = False


class Form1040NRScheduleAInput(BaseFormInput):
    form_code: Literal["1040-NR-Schedule-A"] = "1040-NR-Schedule-A"
    return_name: str = ""
    return_identifying_number: str = ""
    filing_status: NonresidentFilingStatus
    form_1040_nr_line_11b: Decimal = Decimal("0")
    state_local_income_taxes: Decimal = Decimal("0")
    gifts_by_cash_or_check: Decimal = Decimal("0")
    other_than_cash_or_check_gifts: Decimal = Decimal("0")
    charitable_carryover_from_prior_year: Decimal = Decimal("0")
    casualty_and_theft_losses: Decimal = Decimal("0")
    other_itemized_deduction_description: str = ""
    other_itemized_deduction_amount: Decimal = Decimal("0")


class Schedule1Input(BaseFormInput):
    form_code: Literal["1040-Schedule-1"] = "1040-Schedule-1"
    additional_income_items: list[NamedAmount] = Field(default_factory=list)
    adjustment_items: list[NamedAmount] = Field(default_factory=list)


class Schedule1AInput(BaseFormInput):
    form_code: Literal["1040-Schedule-1-A"] = "1040-Schedule-1-A"
    return_name: str = ""
    return_identifying_number: str = ""
    filing_status: FederalFilingStatus
    modified_agi_base: Decimal
    excluded_income_puerto_rico: Decimal = Decimal("0")
    form_2555_line_45: Decimal = Decimal("0")
    form_2555_line_50: Decimal = Decimal("0")
    form_4563_line_15: Decimal = Decimal("0")
    qualified_tips_w2: Decimal = Decimal("0")
    qualified_tips_form_4137: Decimal = Decimal("0")
    qualified_tips_trade_or_business: Decimal = Decimal("0")
    qualified_overtime_w2: Decimal = Decimal("0")
    qualified_overtime_1099: Decimal = Decimal("0")
    vehicle_loan_interest_entries: list[VehicleLoanInterestEntry] = Field(default_factory=list)
    taxpayer_is_eligible_senior: bool = False
    spouse_is_eligible_senior: bool = False


class Schedule2Input(BaseFormInput):
    form_code: Literal["1040-Schedule-2"] = "1040-Schedule-2"
    additional_tax_items: list[NamedAmount] = Field(default_factory=list)


class Schedule3Input(BaseFormInput):
    form_code: Literal["1040-Schedule-3"] = "1040-Schedule-3"
    nonrefundable_credit_items: list[NamedAmount] = Field(default_factory=list)
    payment_items: list[NamedAmount] = Field(default_factory=list)


class ScheduleAInput(BaseFormInput):
    form_code: Literal["1040-Schedule-A"] = "1040-Schedule-A"
    agi: Decimal
    unreimbursed_medical_expenses: Decimal = Decimal("0")
    state_local_income_taxes: Decimal = Decimal("0")
    state_local_sales_taxes: Decimal = Decimal("0")
    real_estate_taxes: Decimal = Decimal("0")
    personal_property_taxes: Decimal = Decimal("0")
    other_taxes: Decimal = Decimal("0")
    mortgage_interest: Decimal = Decimal("0")
    points_not_reported_on_form_1098: Decimal = Decimal("0")
    mortgage_insurance_premiums: Decimal = Decimal("0")
    investment_interest: Decimal = Decimal("0")
    gifts_to_charity_cash: Decimal = Decimal("0")
    gifts_to_charity_other: Decimal = Decimal("0")
    casualty_and_theft_losses: Decimal = Decimal("0")
    other_itemized_deductions: Decimal = Decimal("0")
    salt_cap: Decimal = Decimal("10000")


class ScheduleBInput(BaseFormInput):
    form_code: Literal["1040-Schedule-B"] = "1040-Schedule-B"
    interest_income: list[PayerAmount] = Field(default_factory=list)
    ordinary_dividends: list[PayerAmount] = Field(default_factory=list)
    foreign_accounts: bool = False
    foreign_trust: bool = False


class ScheduleDInput(BaseFormInput):
    form_code: Literal["1040-Schedule-D"] = "1040-Schedule-D"
    short_term_totals: list[NamedAmount] = Field(default_factory=list)
    long_term_totals: list[NamedAmount] = Field(default_factory=list)
    short_term_carryover: Decimal = Decimal("0")
    long_term_carryover: Decimal = Decimal("0")


class Form1040NRScheduleNECInput(BaseFormInput):
    form_code: Literal["1040-NR-Schedule-NEC"] = "1040-NR-Schedule-NEC"
    return_name: str = ""
    return_identifying_number: str = ""
    other_rate_percent: Decimal = Decimal("0")
    income_rows: list[ScheduleNECIncomeRow] = Field(default_factory=list)
    capital_transactions: list[CapitalTransaction] = Field(default_factory=list)
    capital_gain_rate_class: Literal["10", "15", "30", "other"] = "30"


class Form8949Input(BaseFormInput):
    form_code: Literal["8949"] = "8949"
    transactions: list[CapitalTransaction] = Field(default_factory=list)


class ScheduleCInput(BaseFormInput):
    form_code: Literal["1040-Schedule-C"] = "1040-Schedule-C"
    business_name: str
    principal_business_code: str
    accounting_method: Literal["cash", "accrual"] = "cash"
    materially_participates: bool = True
    income_items: list[NamedAmount] = Field(default_factory=list)
    expense_items: list[NamedAmount] = Field(default_factory=list)
    other_expense_items: list[NamedAmount] = Field(default_factory=list)


class ScheduleSEInput(BaseFormInput):
    form_code: Literal["1040-Schedule-SE"] = "1040-Schedule-SE"
    net_profit: Decimal
    optional_farm_income: Decimal = Decimal("0")
    optional_church_employee_income: Decimal = Decimal("0")


class Form4562Input(BaseFormInput):
    form_code: Literal["4562"] = "4562"
    assets: list[DepreciationAsset] = Field(default_factory=list)


class Form8829Input(BaseFormInput):
    form_code: Literal["8829"] = "8829"
    office_area_sqft: Decimal
    home_area_sqft: Decimal
    direct_expenses: list[NamedAmount] = Field(default_factory=list)
    indirect_expenses: list[NamedAmount] = Field(default_factory=list)
    carryover_from_prior_year: Decimal = Decimal("0")
    gross_income_limitation: Decimal = Decimal("0")


class Form8995Input(BaseFormInput):
    form_code: Literal["8995"] = "8995"
    businesses: list[QbiBusiness] = Field(default_factory=list)
    taxable_income_before_qbi: Decimal
    net_capital_gains: Decimal = Decimal("0")


class Form8995AInput(BaseFormInput):
    form_code: Literal["8995-A"] = "8995-A"
    businesses: list[QbiComplexBusiness] = Field(default_factory=list)
    taxable_income_before_qbi: Decimal
    net_capital_gains: Decimal = Decimal("0")


class ScheduleEInput(BaseFormInput):
    form_code: Literal["1040-Schedule-E"] = "1040-Schedule-E"
    rental_activities: list[RentalActivity] = Field(default_factory=list)


class Schedule8812Input(BaseFormInput):
    form_code: Literal["1040-Schedule-8812"] = "1040-Schedule-8812"
    modified_agi: Decimal
    tax_liability_before_credits: Decimal
    earned_income: Decimal = Decimal("0")
    qualifying_children: list[QualifyingChild] = Field(default_factory=list)
    other_dependents: list[OtherDependent] = Field(default_factory=list)
    child_tax_credit_per_child: Decimal = Decimal("2000")
    credit_for_other_dependents: Decimal = Decimal("500")
    phaseout_threshold: Decimal = Decimal("400000")


class ScheduleEICInput(BaseFormInput):
    form_code: Literal["1040-Schedule-EIC"] = "1040-Schedule-EIC"
    return_name: str = ""
    return_ssn: str = ""
    filing_status: FederalFilingStatus
    earned_income: Decimal
    agi: Decimal
    investment_income: Decimal = Decimal("0")
    qualifying_children: list[QualifyingChild] = Field(default_factory=list)


class Form8862SectionB(TaxModel):
    taxpayer_main_home_days_in_us: int | None = None
    spouse_main_home_days_in_us: int | None = None
    taxpayer_age: int | None = None
    spouse_age: int | None = None
    taxpayer_can_be_claimed_as_dependent: bool | None = None
    spouse_can_be_claimed_as_dependent: bool | None = None


class Form8862CreditChild(TaxModel):
    name: str
    lived_with_you_more_than_half_year: bool = True
    qualifies_for_credit: bool = True
    is_dependent: bool = True
    is_us_citizen_national_or_resident: bool = True


class Form8862OtherDependent(TaxModel):
    name: str
    is_dependent: bool = True
    is_us_citizen_national_or_resident: bool = True


class Form8862AotcStudent(TaxModel):
    name: str
    is_eligible_student: bool = True
    hope_or_aotc_claimed_for_any_4_prior_years: bool = False


class Form2441Input(BaseFormInput):
    form_code: Literal["2441"] = "2441"
    taxpayer_earned_income: Decimal
    spouse_earned_income: Decimal = Decimal("0")
    providers: list[CareProvider] = Field(default_factory=list)
    qualifying_persons: list[CareDependent] = Field(default_factory=list)
    dependent_care_benefits: Decimal = Decimal("0")
    agi: Decimal = Decimal("0")


class Form8863Input(BaseFormInput):
    form_code: Literal["8863"] = "8863"
    filing_status: FederalFilingStatus
    modified_agi: Decimal
    students: list[StudentExpense] = Field(default_factory=list)


class Form8889Input(BaseFormInput):
    form_code: Literal["8889"] = "8889"
    coverage_type: Literal["self", "family"]
    months_eligible: int = 12
    taxpayer_contributions: Decimal = Decimal("0")
    employer_contributions: Decimal = Decimal("0")
    distributions: Decimal = Decimal("0")
    qualified_medical_expenses: Decimal = Decimal("0")
    age_55_or_older: bool = False
    prior_year_excess_contributions: Decimal = Decimal("0")


class Form8962Input(BaseFormInput):
    form_code: Literal["8962"] = "8962"
    household_income: Decimal
    household_size: int
    federal_poverty_line: Decimal
    annual_contribution_percentage: Decimal
    monthly_entries: list[MonthlyMarketplaceEntry] = Field(default_factory=list)


class Form8862Input(BaseFormInput):
    form_code: Literal["8862"] = "8862"
    return_name: str = ""
    return_ssn: str = ""
    credit_type: Literal["ctc", "odc", "aotc", "eic"]
    credit_claims: list[Literal["eic", "ctc_odc", "aotc"]] = Field(default_factory=list)
    tax_year_of_disallowance: int
    reason_disallowance_resolved: str
    part_ii_only_income_or_investment_income_issue: bool = False
    part_ii_taxpayer_or_spouse_can_be_claimed_as_qualifying_child: bool = False
    qualifying_children: list[QualifyingChild] = Field(default_factory=list)
    part_ii_section_b: Form8862SectionB | None = None
    ctc_children: list[Form8862CreditChild] = Field(default_factory=list)
    odc_dependents: list[Form8862OtherDependent] = Field(default_factory=list)
    aotc_students: list[Form8862AotcStudent] = Field(default_factory=list)
