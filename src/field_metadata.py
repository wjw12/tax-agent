"""Field-level metadata and inter-form wiring for all supported 2025 forms.

Layer 1 — Field Classification
    Every input model field is classified by its *role*: where the value
    must come from.  An agent can query ``get_field_meta`` or
    ``get_fields_by_role`` to decide what still needs filling and how.

Layer 2 — Inter-Form Wiring
    ``FORM_WIRES`` declares every output-line → input-field connection
    between forms.  ``get_form_dependencies`` and ``get_build_order``
    derive the dependency graph and a safe processing order from this
    single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Literal


# ---------------------------------------------------------------------------
# Layer 1 — field role taxonomy
# ---------------------------------------------------------------------------

class FieldRole(str, Enum):
    """Classification of a form-input field by its value origin."""
    FORM_IDENTITY = "form_identity"
    TAXPAYER_FACT = "taxpayer_fact"
    SOURCE = "source"
    CROSS_FORM = "cross_form"
    COMPUTED_INPUT = "computed_input"
    DERIVED = "derived"


@dataclass(frozen=True)
class CrossFormRef:
    """Pointer to the producing form and processor output line."""
    source_form: str
    source_line: str
    notes: str = ""


@dataclass(frozen=True)
class FieldMeta:
    """Metadata for a single input-model field."""
    role: FieldRole
    description: str = ""
    cross_form_ref: CrossFormRef | None = None
    alternative_refs: tuple[CrossFormRef, ...] = ()
    notes: str = ""


# ---------------------------------------------------------------------------
# Layer 1 — per-form field metadata
# ---------------------------------------------------------------------------

_IDENTITY = FieldMeta(FieldRole.FORM_IDENTITY)

FIELD_METADATA: dict[str, dict[str, FieldMeta]] = {

    # ------------------------------------------------------------------
    # Form 1040
    # ------------------------------------------------------------------
    "1040": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "taxpayer": FieldMeta(FieldRole.TAXPAYER_FACT),
        "spouse": FieldMeta(FieldRole.TAXPAYER_FACT),
        "dependents": FieldMeta(FieldRole.TAXPAYER_FACT),
        "digital_assets": FieldMeta(FieldRole.TAXPAYER_FACT),
        "wages": FieldMeta(FieldRole.SOURCE, description="W-2 box 1"),
        "taxable_interest": FieldMeta(
            FieldRole.SOURCE,
            description="1099-INT or Schedule B line 4",
            cross_form_ref=CrossFormRef("1040-Schedule-B", "2"),
            notes="Use Schedule B total when multiple payers exist.",
        ),
        "ordinary_dividends": FieldMeta(
            FieldRole.SOURCE,
            description="1099-DIV or Schedule B line 6",
            cross_form_ref=CrossFormRef("1040-Schedule-B", "6"),
            notes="Use Schedule B total when multiple payers exist.",
        ),
        "qualified_dividends": FieldMeta(FieldRole.SOURCE, description="1099-DIV box 1b"),
        "ira_distributions": FieldMeta(FieldRole.SOURCE, description="1099-R"),
        "taxable_ira_distributions": FieldMeta(FieldRole.SOURCE, description="1099-R taxable amount"),
        "pension_annuity_income": FieldMeta(FieldRole.SOURCE, description="1099-R"),
        "taxable_pension_annuity_income": FieldMeta(FieldRole.SOURCE, description="1099-R taxable amount"),
        "social_security_benefits": FieldMeta(FieldRole.SOURCE, description="SSA-1099 box 5"),
        "taxable_social_security_benefits": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Computed from Social Security Benefits Worksheet",
            notes="The processor does NOT derive this; the agent must compute it.",
        ),
        "capital_gain_distributions": FieldMeta(
            FieldRole.SOURCE,
            description="Direct capital gain distributions when Schedule D is not required",
            notes="Use the direct-source path only when Schedule D is not required for line 7.",
        ),
        "capital_gain_or_loss": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Final Form 1040 line 7 amount after Schedule D/direct-distribution assembly",
            cross_form_ref=CrossFormRef("1040-Schedule-D", "16"),
            alternative_refs=(CrossFormRef("1040-Schedule-D", "21"),),
            notes=(
                "Assemble line 7 explicitly. If Schedule D exists, use the Schedule D result "
                "(and the line 21 loss cap when line 16 is a loss). Otherwise use "
                "capital_gain_distributions. Do not overload this field as both a Schedule D "
                "wire and a direct-source distribution amount."
            ),
        ),
        "uses_form_2555": FieldMeta(
            FieldRole.TAXPAYER_FACT,
            description="Whether the return uses Form 2555",
            notes="Form 2555 cases cannot use the standard TY2025 helper without the Foreign Earned Income Tax Worksheet.",
        ),
        "schedule_d_line_18": FieldMeta(
            FieldRole.SOURCE,
            description="Schedule D line 18",
            notes="Capture explicitly for Schedule D Tax Worksheet trigger validation.",
        ),
        "schedule_d_line_19": FieldMeta(
            FieldRole.SOURCE,
            description="Schedule D line 19",
            notes="Capture explicitly for Schedule D Tax Worksheet trigger validation.",
        ),
        "has_form_4952_line_4g": FieldMeta(
            FieldRole.SOURCE,
            description="Whether Form 4952 line 4g is present",
            notes="Capture explicitly for Schedule D Tax Worksheet trigger validation even if Schedule D is not filed.",
        ),
        "requires_schedule_d_tax_worksheet": FieldMeta(
            FieldRole.DERIVED,
            description="Derived Schedule D Tax Worksheet trigger flag",
            notes="Derive deterministically from Form 4952 line 4g, Schedule D lines 18/19, and Schedule D lines 15/16.",
        ),
        "schedule_1_additional_income": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule 1 line 10",
            cross_form_ref=CrossFormRef("1040-Schedule-1", "10"),
            notes="Use 0 only when Schedule 1 is not needed.",
        ),
        "schedule_1_adjustments": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule 1 line 26",
            cross_form_ref=CrossFormRef("1040-Schedule-1", "26"),
            notes="Use 0 only when Schedule 1 is not needed.",
        ),
        "itemized_deductions": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule A line 17",
            cross_form_ref=CrossFormRef("1040-Schedule-A", "17"),
            notes="Set to 0 when taking the standard deduction.",
        ),
        "standard_deduction": FieldMeta(
            FieldRole.TAXPAYER_FACT,
            description="Determined by filing status, age, and dependency status",
            notes="2025: single=$15,750, MFS=$15,750, MFJ=$31,500, QSS=$31,500, HOH=$23,625.",
        ),
        "qbi_deduction": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Form 8995 line 15 or Form 8995-A line 26",
            cross_form_ref=CrossFormRef("8995", "15"),
            alternative_refs=(CrossFormRef("8995-A", "26"),),
            notes="Use 0 when no QBI exists.",
        ),
        "tax_before_credits": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Income tax from tax tables or qualified dividends worksheet",
            notes=(
                "CRITICAL: The 1040 processor does NOT compute this. "
                "The agent MUST compute TY2025 Form 1040 line 16 using "
                "the shared helper in src.federal_income_tax. Use the "
                "ordinary brackets only when the qualified-dividends/capital-"
                "gain worksheet does not apply. See workspace/"
                "FORM_1040_2025_TAX.md. Leaving this at 0 when taxable "
                "income > 0 will produce an incorrect return."
            ),
        ),
        "nonrefundable_credits": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule 3 line 8 or direct credit amount",
            cross_form_ref=CrossFormRef("1040-Schedule-3", "8"),
            notes="Use 0 when no nonrefundable credits apply.",
        ),
        "other_taxes": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule 2 line 21 or SE tax from Schedule SE line 12",
            cross_form_ref=CrossFormRef("1040-Schedule-2", "21"),
            alternative_refs=(
                CrossFormRef(
                    "1040-Schedule-SE", "12",
                    notes="Use directly when Schedule 2 is not needed",
                ),
            ),
            notes=(
                "This is the FULL self-employment tax (line 12), NOT the "
                "deductible half (line 13). Using the deductible half here "
                "is a common agent error."
            ),
        ),
        "federal_withholding": FieldMeta(FieldRole.SOURCE, description="W-2 box 2 + 1099 withholding"),
        "estimated_tax_payments": FieldMeta(FieldRole.TAXPAYER_FACT),
        "refundable_credits": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule 3 line 15 or direct refundable credit amount",
            cross_form_ref=CrossFormRef("1040-Schedule-3", "15"),
            notes="Use 0 when no refundable credits apply.",
        ),
        "amount_applied_from_prior_year": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Form 1040-SR (inherits 1040 fields)
    # ------------------------------------------------------------------
    "1040-SR": {},  # populated below via inheritance

    # ------------------------------------------------------------------
    # Form 1040-NR
    # ------------------------------------------------------------------
    "1040-NR": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "residency_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "taxpayer": FieldMeta(FieldRole.TAXPAYER_FACT),
        "dependents": FieldMeta(FieldRole.TAXPAYER_FACT),
        "digital_assets": FieldMeta(FieldRole.TAXPAYER_FACT),
        "country_of_citizenship": FieldMeta(FieldRole.TAXPAYER_FACT),
        "country_of_tax_residence": FieldMeta(FieldRole.TAXPAYER_FACT),
        "visa_type": FieldMeta(FieldRole.TAXPAYER_FACT),
        "days_present_in_us": FieldMeta(FieldRole.TAXPAYER_FACT),
        "claims_treaty_benefits": FieldMeta(FieldRole.TAXPAYER_FACT),
        "treaty_country": FieldMeta(FieldRole.TAXPAYER_FACT),
        "has_dual_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "qualifying_person_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "wages": FieldMeta(FieldRole.SOURCE, description="W-2 box 1"),
        "taxable_interest": FieldMeta(FieldRole.SOURCE, description="1099-INT"),
        "ordinary_dividends": FieldMeta(FieldRole.SOURCE, description="1099-DIV"),
        "qualified_dividends": FieldMeta(FieldRole.SOURCE, description="1099-DIV box 1b"),
        "ira_distributions": FieldMeta(FieldRole.SOURCE, description="1099-R"),
        "taxable_ira_distributions": FieldMeta(FieldRole.SOURCE),
        "pension_annuity_income": FieldMeta(FieldRole.SOURCE),
        "taxable_pension_annuity_income": FieldMeta(FieldRole.SOURCE),
        "capital_gain_or_loss": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-D", "16"),
        ),
        "schedule_1_additional_income": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-1", "10"),
        ),
        "treaty_exempt_income": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-NR-Schedule-OI", "l1e"),
            notes="Total treaty-exempt income from Schedule OI.",
        ),
        "schedule_1_adjustments": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-1", "26"),
        ),
        "itemized_deductions": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-NR-Schedule-A", "8"),
        ),
        "standard_deduction": FieldMeta(FieldRole.TAXPAYER_FACT),
        "qbi_deduction": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("8995", "15"),
            alternative_refs=(CrossFormRef("8995-A", "26"),),
        ),
        "estate_or_trust_exemption": FieldMeta(FieldRole.TAXPAYER_FACT),
        "schedule_1a_additional_deductions": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-1-A", "38"),
        ),
        "tax_before_credits": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            notes="The 1040-NR processor does NOT compute this from tax tables.",
        ),
        "schedule_2_additional_taxes": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-2", "21"),
        ),
        "child_tax_credit_or_other_dependent_credit": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-8812", "14"),
        ),
        "schedule_3_nonrefundable_credits": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-3", "8"),
        ),
        "nec_tax": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-NR-Schedule-NEC", "15"),
        ),
        "other_taxes": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-2", "21"),
            alternative_refs=(CrossFormRef("1040-Schedule-SE", "12"),),
        ),
        "transportation_tax": FieldMeta(FieldRole.SOURCE),
        "withholding_w2": FieldMeta(FieldRole.SOURCE, description="W-2 box 2"),
        "withholding_1099": FieldMeta(FieldRole.SOURCE, description="1099 withholding"),
        "withholding_other_forms": FieldMeta(FieldRole.SOURCE),
        "withholding_8805": FieldMeta(FieldRole.SOURCE),
        "withholding_8288a": FieldMeta(FieldRole.SOURCE),
        "withholding_1042s": FieldMeta(FieldRole.SOURCE, description="1042-S box 7"),
        "estimated_tax_payments": FieldMeta(FieldRole.TAXPAYER_FACT),
        "additional_child_tax_credit": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-8812", "27"),
        ),
        "form_1040c_credit": FieldMeta(FieldRole.SOURCE),
        "refundable_adoption_credit": FieldMeta(FieldRole.SOURCE),
        "schedule_3_refundable_credits": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-3", "15"),
        ),
        "amount_applied_to_next_year": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Schedule 1
    # ------------------------------------------------------------------
    "1040-Schedule-1": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "additional_income_items": FieldMeta(
            FieldRole.SOURCE,
            description="List of additional income items",
            notes=(
                "Common cross-form constituents: Schedule C line 31 "
                "(net profit), Schedule E line 21 (rental income/loss), "
                "Form 8949/Schedule D capital gains. Each item in the list "
                "may originate from a different source form or document."
            ),
        ),
        "adjustment_items": FieldMeta(
            FieldRole.SOURCE,
            description="List of adjustment items",
            notes=(
                "Common cross-form constituents: Schedule SE line 13 "
                "(deductible half of SE tax), Form 8889 line 13 (HSA "
                "deduction), self-employed health insurance deduction. "
                "Each item may originate from a different source form."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Schedule 1-A
    # ------------------------------------------------------------------
    "1040-Schedule-1-A": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_identifying_number": FieldMeta(FieldRole.TAXPAYER_FACT),
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "modified_agi_base": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040", "11"),
            notes="Line 11 AGI from Form 1040, 1040-SR, or 1040-NR.",
        ),
        "excluded_income_puerto_rico": FieldMeta(FieldRole.SOURCE),
        "form_2555_line_45": FieldMeta(FieldRole.SOURCE),
        "form_2555_line_50": FieldMeta(FieldRole.SOURCE),
        "form_4563_line_15": FieldMeta(FieldRole.SOURCE),
        "qualified_tips_w2": FieldMeta(FieldRole.SOURCE, description="W-2"),
        "qualified_tips_form_4137": FieldMeta(FieldRole.SOURCE),
        "qualified_tips_trade_or_business": FieldMeta(FieldRole.SOURCE),
        "qualified_overtime_w2": FieldMeta(FieldRole.SOURCE, description="W-2"),
        "qualified_overtime_1099": FieldMeta(FieldRole.SOURCE),
        "vehicle_loan_interest_entries": FieldMeta(FieldRole.SOURCE),
        "taxpayer_is_eligible_senior": FieldMeta(FieldRole.TAXPAYER_FACT),
        "spouse_is_eligible_senior": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Schedule 2
    # ------------------------------------------------------------------
    "1040-Schedule-2": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "additional_tax_items": FieldMeta(
            FieldRole.SOURCE,
            description="List of additional tax items",
            notes=(
                "Common cross-form constituent: Schedule SE line 12 "
                "(self-employment tax). This is the FULL SE tax amount."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Schedule 3
    # ------------------------------------------------------------------
    "1040-Schedule-3": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "nonrefundable_credit_items": FieldMeta(
            FieldRole.SOURCE,
            description="List of nonrefundable credit items",
            notes=(
                "Common cross-form constituents: Form 2441 line 13 "
                "(child care credit), Form 8863 line 19 (education credits)."
            ),
        ),
        "payment_items": FieldMeta(
            FieldRole.SOURCE,
            description="List of other payments and refundable credits",
        ),
    },

    # ------------------------------------------------------------------
    # Schedule A
    # ------------------------------------------------------------------
    "1040-Schedule-A": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "agi": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Adjusted gross income from Form 1040 line 11",
            cross_form_ref=CrossFormRef("1040", "11"),
        ),
        "unreimbursed_medical_expenses": FieldMeta(FieldRole.SOURCE),
        "state_local_income_taxes": FieldMeta(FieldRole.SOURCE),
        "state_local_sales_taxes": FieldMeta(FieldRole.SOURCE),
        "real_estate_taxes": FieldMeta(FieldRole.SOURCE, description="1098 or tax bill"),
        "personal_property_taxes": FieldMeta(FieldRole.SOURCE),
        "other_taxes": FieldMeta(FieldRole.SOURCE),
        "mortgage_interest": FieldMeta(FieldRole.SOURCE, description="1098 box 1"),
        "points_not_reported_on_form_1098": FieldMeta(FieldRole.SOURCE),
        "mortgage_insurance_premiums": FieldMeta(FieldRole.SOURCE),
        "investment_interest": FieldMeta(FieldRole.SOURCE),
        "gifts_to_charity_cash": FieldMeta(FieldRole.SOURCE),
        "gifts_to_charity_other": FieldMeta(FieldRole.SOURCE),
        "casualty_and_theft_losses": FieldMeta(FieldRole.SOURCE),
        "other_itemized_deductions": FieldMeta(FieldRole.SOURCE),
        "salt_cap": FieldMeta(
            FieldRole.TAXPAYER_FACT,
            notes="2025: $40,000 default ($20,000 MFS).",
        ),
    },

    # ------------------------------------------------------------------
    # Schedule B
    # ------------------------------------------------------------------
    "1040-Schedule-B": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "interest_income": FieldMeta(FieldRole.SOURCE, description="1099-INT payer list"),
        "ordinary_dividends": FieldMeta(FieldRole.SOURCE, description="1099-DIV payer list"),
        "foreign_accounts": FieldMeta(FieldRole.TAXPAYER_FACT),
        "foreign_trust": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Schedule C
    # ------------------------------------------------------------------
    "1040-Schedule-C": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "business_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "principal_business_code": FieldMeta(FieldRole.TAXPAYER_FACT),
        "accounting_method": FieldMeta(FieldRole.TAXPAYER_FACT),
        "materially_participates": FieldMeta(FieldRole.TAXPAYER_FACT),
        "income_items": FieldMeta(
            FieldRole.SOURCE,
            description="1099-NEC, 1099-K, direct invoices, other gross receipts",
        ),
        "expense_items": FieldMeta(FieldRole.SOURCE, description="Receipts and records"),
        "other_expense_items": FieldMeta(FieldRole.SOURCE),
    },

    # ------------------------------------------------------------------
    # Schedule D
    # ------------------------------------------------------------------
    "1040-Schedule-D": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "short_term_totals": FieldMeta(
            FieldRole.SOURCE,
            description="Short-term capital gain/loss totals",
            notes="May include cross-form input from Form 8949 short_gain.",
        ),
        "long_term_totals": FieldMeta(
            FieldRole.SOURCE,
            description="Long-term capital gain/loss totals",
            notes="May include cross-form input from Form 8949 long_gain.",
        ),
        "short_term_carryover": FieldMeta(FieldRole.TAXPAYER_FACT),
        "long_term_carryover": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Schedule E
    # ------------------------------------------------------------------
    "1040-Schedule-E": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "rental_activities": FieldMeta(FieldRole.SOURCE, description="Rental property records"),
    },

    # ------------------------------------------------------------------
    # Schedule SE
    # ------------------------------------------------------------------
    "1040-Schedule-SE": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "net_profit": FieldMeta(
            FieldRole.CROSS_FORM,
            description="Schedule C line 31",
            cross_form_ref=CrossFormRef("1040-Schedule-C", "31"),
            notes="Net profit or loss from self-employment.",
        ),
        "optional_farm_income": FieldMeta(FieldRole.SOURCE),
        "optional_church_employee_income": FieldMeta(FieldRole.SOURCE),
    },

    # ------------------------------------------------------------------
    # Schedule 8812
    # ------------------------------------------------------------------
    "1040-Schedule-8812": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "modified_agi": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040", "11"),
            notes="AGI from Form 1040 line 11.",
        ),
        "tax_liability_before_credits": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            notes="Tax liability before credits, from 1040 computation.",
        ),
        "earned_income": FieldMeta(FieldRole.SOURCE),
        "qualifying_children": FieldMeta(FieldRole.TAXPAYER_FACT),
        "other_dependents": FieldMeta(FieldRole.TAXPAYER_FACT),
        "child_tax_credit_per_child": FieldMeta(FieldRole.TAXPAYER_FACT, notes="2025: $2,200"),
        "credit_for_other_dependents": FieldMeta(FieldRole.TAXPAYER_FACT, notes="2025: $500"),
        "phaseout_threshold": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Schedule EIC
    # ------------------------------------------------------------------
    "1040-Schedule-EIC": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_ssn": FieldMeta(FieldRole.TAXPAYER_FACT),
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "earned_income": FieldMeta(FieldRole.SOURCE),
        "agi": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040", "11"),
        ),
        "investment_income": FieldMeta(FieldRole.SOURCE),
        "qualifying_children": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Form 8949
    # ------------------------------------------------------------------
    "8949": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "transactions": FieldMeta(
            FieldRole.SOURCE,
            description="Brokerage 1099-B, gain/loss reports, crypto records",
        ),
    },

    # ------------------------------------------------------------------
    # Form 4562
    # ------------------------------------------------------------------
    "4562": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "assets": FieldMeta(FieldRole.SOURCE, description="Asset records for depreciation"),
    },

    # ------------------------------------------------------------------
    # Form 8829
    # ------------------------------------------------------------------
    "8829": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "office_area_sqft": FieldMeta(FieldRole.TAXPAYER_FACT),
        "home_area_sqft": FieldMeta(FieldRole.TAXPAYER_FACT),
        "direct_expenses": FieldMeta(FieldRole.SOURCE),
        "indirect_expenses": FieldMeta(FieldRole.SOURCE),
        "carryover_from_prior_year": FieldMeta(FieldRole.TAXPAYER_FACT),
        "gross_income_limitation": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-C", "31"),
            notes="Gross income limitation for home office deduction.",
        ),
    },

    # ------------------------------------------------------------------
    # Form 8995
    # ------------------------------------------------------------------
    "8995": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "businesses": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Structured QBI business entries",
            notes=(
                "Build with src.qbi.build_qbi_form_input_2025 or "
                "src.qbi.build_qbi_business_assembly_from_forms. "
                "For a sole proprietorship, qualified_business_income is "
                "typically Schedule C line 31 minus Schedule SE line 13, "
                "minus any IRC 224 qualified tips deduction. It is NOT the "
                "same as Schedule C line 31."
            ),
        ),
        "taxable_income_before_qbi": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Taxable income before QBI deduction",
            notes=(
                "Computed as AGI minus the greater of standard or itemized "
                "deductions. Must be computed by the agent; the 8995 "
                "processor does not derive it. For TY2025 use Form 8995 only "
                "when taxable_income_before_qbi is at or below $394,600 for "
                "MFJ or $197,300 for all other returns; otherwise use 8995-A."
            ),
        ),
        "net_capital_gains": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-D", "16"),
            notes="Use 0 when no capital transactions exist.",
        ),
    },

    # ------------------------------------------------------------------
    # Form 8995-A
    # ------------------------------------------------------------------
    "8995-A": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "businesses": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            description="Structured QBI business entries with wage/property data",
            notes=(
                "Build with src.qbi.build_qbi_form_input_2025 or "
                "src.qbi.build_qbi_business_assembly_from_forms. "
                "Use 8995-A when TY2025 taxable_income_before_qbi exceeds "
                "$394,600 for MFJ or $197,300 for all other returns."
            ),
        ),
        "taxable_income_before_qbi": FieldMeta(
            FieldRole.COMPUTED_INPUT,
            notes=(
                "Computed as AGI minus the greater of standard or itemized "
                "deductions. Must be computed by the agent. Use 8995-A when "
                "TY2025 taxable_income_before_qbi exceeds $394,600 for MFJ or "
                "$197,300 for all other returns."
            ),
        ),
        "net_capital_gains": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-Schedule-D", "16"),
        ),
    },

    # ------------------------------------------------------------------
    # Form 2441
    # ------------------------------------------------------------------
    "2441": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "taxpayer_earned_income": FieldMeta(FieldRole.SOURCE),
        "spouse_earned_income": FieldMeta(FieldRole.SOURCE),
        "providers": FieldMeta(FieldRole.SOURCE),
        "qualifying_persons": FieldMeta(FieldRole.SOURCE),
        "dependent_care_benefits": FieldMeta(FieldRole.SOURCE, description="W-2 box 10"),
        "agi": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040", "11"),
        ),
    },

    # ------------------------------------------------------------------
    # Form 8863
    # ------------------------------------------------------------------
    "8863": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "modified_agi": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040", "11"),
            notes="MAGI for education credits (AGI from 1040 line 11).",
        ),
        "students": FieldMeta(FieldRole.SOURCE, description="1098-T and student records"),
    },

    # ------------------------------------------------------------------
    # Form 8889
    # ------------------------------------------------------------------
    "8889": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "coverage_type": FieldMeta(FieldRole.TAXPAYER_FACT),
        "months_eligible": FieldMeta(FieldRole.TAXPAYER_FACT),
        "taxpayer_contributions": FieldMeta(FieldRole.SOURCE, description="5498-SA"),
        "employer_contributions": FieldMeta(FieldRole.SOURCE, description="W-2 box 12 code W"),
        "distributions": FieldMeta(FieldRole.SOURCE, description="1099-SA"),
        "qualified_medical_expenses": FieldMeta(FieldRole.SOURCE),
        "age_55_or_older": FieldMeta(FieldRole.TAXPAYER_FACT),
        "prior_year_excess_contributions": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # Form 8962
    # ------------------------------------------------------------------
    "8962": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "household_income": FieldMeta(FieldRole.SOURCE),
        "household_size": FieldMeta(FieldRole.TAXPAYER_FACT),
        "federal_poverty_line": FieldMeta(FieldRole.TAXPAYER_FACT),
        "annual_contribution_percentage": FieldMeta(FieldRole.COMPUTED_INPUT),
        "monthly_entries": FieldMeta(FieldRole.SOURCE, description="1095-A"),
    },

    # ------------------------------------------------------------------
    # Form 8862
    # ------------------------------------------------------------------
    "8862": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_ssn": FieldMeta(FieldRole.TAXPAYER_FACT),
        "credit_type": FieldMeta(FieldRole.TAXPAYER_FACT),
        "credit_claims": FieldMeta(FieldRole.TAXPAYER_FACT),
        "tax_year_of_disallowance": FieldMeta(FieldRole.TAXPAYER_FACT),
        "reason_disallowance_resolved": FieldMeta(FieldRole.TAXPAYER_FACT),
        "part_ii_only_income_or_investment_income_issue": FieldMeta(FieldRole.TAXPAYER_FACT),
        "part_ii_taxpayer_or_spouse_can_be_claimed_as_qualifying_child": FieldMeta(FieldRole.TAXPAYER_FACT),
        "qualifying_children": FieldMeta(FieldRole.TAXPAYER_FACT),
        "part_ii_section_b": FieldMeta(FieldRole.TAXPAYER_FACT),
        "ctc_children": FieldMeta(FieldRole.TAXPAYER_FACT),
        "odc_dependents": FieldMeta(FieldRole.TAXPAYER_FACT),
        "aotc_students": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # 1040-NR Schedule OI
    # ------------------------------------------------------------------
    "1040-NR-Schedule-OI": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_identifying_number": FieldMeta(FieldRole.TAXPAYER_FACT),
        "citizenship_countries": FieldMeta(FieldRole.TAXPAYER_FACT),
        "tax_residence_country": FieldMeta(FieldRole.TAXPAYER_FACT),
        "visa_type": FieldMeta(FieldRole.TAXPAYER_FACT),
        "applied_for_green_card": FieldMeta(FieldRole.TAXPAYER_FACT),
        "was_us_citizen": FieldMeta(FieldRole.TAXPAYER_FACT),
        "was_green_card_holder": FieldMeta(FieldRole.TAXPAYER_FACT),
        "changed_visa_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "visa_status_change_details": FieldMeta(FieldRole.TAXPAYER_FACT),
        "entry_departure_dates": FieldMeta(FieldRole.TAXPAYER_FACT),
        "commuter_from_canada": FieldMeta(FieldRole.TAXPAYER_FACT),
        "commuter_from_mexico": FieldMeta(FieldRole.TAXPAYER_FACT),
        "days_in_us_2023": FieldMeta(FieldRole.TAXPAYER_FACT),
        "days_in_us_2024": FieldMeta(FieldRole.TAXPAYER_FACT),
        "days_in_us_2025": FieldMeta(FieldRole.TAXPAYER_FACT),
        "previously_filed_us_return": FieldMeta(FieldRole.TAXPAYER_FACT),
        "prior_filing_year_and_form": FieldMeta(FieldRole.TAXPAYER_FACT),
        "filing_for_trust": FieldMeta(FieldRole.TAXPAYER_FACT),
        "trust_had_us_or_foreign_owner_or_distribution": FieldMeta(FieldRole.TAXPAYER_FACT),
        "received_total_compensation_over_250k": FieldMeta(FieldRole.TAXPAYER_FACT),
        "used_alternative_compensation_sourcing_method": FieldMeta(FieldRole.TAXPAYER_FACT),
        "treaty_claims": FieldMeta(FieldRole.SOURCE),
        "taxed_on_treaty_exempt_income_in_foreign_country": FieldMeta(FieldRole.TAXPAYER_FACT),
        "claiming_competent_authority_benefits": FieldMeta(FieldRole.TAXPAYER_FACT),
        "real_property_election_first_year": FieldMeta(FieldRole.TAXPAYER_FACT),
        "real_property_election_continuing": FieldMeta(FieldRole.TAXPAYER_FACT),
    },

    # ------------------------------------------------------------------
    # 1040-NR Schedule A
    # ------------------------------------------------------------------
    "1040-NR-Schedule-A": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_identifying_number": FieldMeta(FieldRole.TAXPAYER_FACT),
        "filing_status": FieldMeta(FieldRole.TAXPAYER_FACT),
        "form_1040_nr_line_11b": FieldMeta(
            FieldRole.CROSS_FORM,
            cross_form_ref=CrossFormRef("1040-NR", "11b"),
        ),
        "state_local_income_taxes": FieldMeta(FieldRole.SOURCE),
        "gifts_by_cash_or_check": FieldMeta(FieldRole.SOURCE),
        "other_than_cash_or_check_gifts": FieldMeta(FieldRole.SOURCE),
        "charitable_carryover_from_prior_year": FieldMeta(FieldRole.TAXPAYER_FACT),
        "casualty_and_theft_losses": FieldMeta(FieldRole.SOURCE),
        "other_itemized_deduction_description": FieldMeta(FieldRole.SOURCE),
        "other_itemized_deduction_amount": FieldMeta(FieldRole.SOURCE),
    },

    # ------------------------------------------------------------------
    # 1040-NR Schedule NEC
    # ------------------------------------------------------------------
    "1040-NR-Schedule-NEC": {
        "form_code": _IDENTITY,
        "tax_year": _IDENTITY,
        "return_name": FieldMeta(FieldRole.TAXPAYER_FACT),
        "return_identifying_number": FieldMeta(FieldRole.TAXPAYER_FACT),
        "other_rate_percent": FieldMeta(FieldRole.TAXPAYER_FACT),
        "income_rows": FieldMeta(FieldRole.SOURCE),
        "capital_transactions": FieldMeta(FieldRole.SOURCE),
        "capital_gain_rate_class": FieldMeta(FieldRole.TAXPAYER_FACT),
    },
}

# 1040-SR inherits all 1040 field metadata
FIELD_METADATA["1040-SR"] = dict(FIELD_METADATA["1040"])


# ---------------------------------------------------------------------------
# Layer 2 — inter-form wiring
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FormWire:
    """A single output-line -> input-field connection between two forms."""
    source_form: str
    source_line: str
    target_form: str
    target_field: str
    target_is_list_item: bool = False
    item_description: str = ""
    notes: str = ""


FORM_WIRES: tuple[FormWire, ...] = (
    # Schedule C -> Schedule SE
    FormWire("1040-Schedule-C", "31", "1040-Schedule-SE", "net_profit"),

    # Schedule C -> Schedule 1 (as list item)
    FormWire(
        "1040-Schedule-C", "31", "1040-Schedule-1", "additional_income_items",
        target_is_list_item=True, item_description="Net profit from Schedule C",
    ),

    # Schedule SE -> Schedule 1 adjustment (as list item)
    FormWire(
        "1040-Schedule-SE", "13", "1040-Schedule-1", "adjustment_items",
        target_is_list_item=True,
        item_description="Deductible part of self-employment tax",
    ),

    # Schedule SE -> 1040 other_taxes (direct when no Schedule 2)
    FormWire(
        "1040-Schedule-SE", "12", "1040", "other_taxes",
        notes="Full SE tax. Use Schedule 2 as intermediary for complex returns.",
    ),

    # Schedule SE -> Schedule 2 (as list item)
    FormWire(
        "1040-Schedule-SE", "12", "1040-Schedule-2", "additional_tax_items",
        target_is_list_item=True, item_description="Self-employment tax",
    ),

    # Schedule 1 -> 1040
    FormWire("1040-Schedule-1", "10", "1040", "schedule_1_additional_income"),
    FormWire("1040-Schedule-1", "26", "1040", "schedule_1_adjustments"),

    # Schedule 2 -> 1040
    FormWire("1040-Schedule-2", "21", "1040", "other_taxes"),

    # Schedule 3 -> 1040
    FormWire("1040-Schedule-3", "8", "1040", "nonrefundable_credits"),
    FormWire("1040-Schedule-3", "15", "1040", "refundable_credits"),

    # Schedule A -> 1040
    FormWire("1040-Schedule-A", "17", "1040", "itemized_deductions"),

    # Schedule B -> 1040
    FormWire("1040-Schedule-B", "2", "1040", "taxable_interest"),
    FormWire("1040-Schedule-B", "6", "1040", "ordinary_dividends"),

    # Schedule D -> 1040
    FormWire("1040-Schedule-D", "16", "1040", "capital_gain_or_loss"),

    # Form 8995 -> 1040
    FormWire("8995", "15", "1040", "qbi_deduction"),

    # Form 8995-A -> 1040
    FormWire("8995-A", "26", "1040", "qbi_deduction"),

    # Schedule 8812 -> 1040-NR
    FormWire("1040-Schedule-8812", "14", "1040-NR", "child_tax_credit_or_other_dependent_credit"),
    FormWire("1040-Schedule-8812", "27", "1040-NR", "additional_child_tax_credit"),

    # Schedule OI -> 1040-NR
    FormWire("1040-NR-Schedule-OI", "l1e", "1040-NR", "treaty_exempt_income"),

    # Schedule NEC -> 1040-NR
    FormWire("1040-NR-Schedule-NEC", "15", "1040-NR", "nec_tax"),

    # 1040-NR Schedule A -> 1040-NR
    FormWire("1040-NR-Schedule-A", "8", "1040-NR", "itemized_deductions"),

    # Schedule 1-A -> 1040-NR
    FormWire("1040-Schedule-1-A", "38", "1040-NR", "schedule_1a_additional_deductions"),

    # Schedule 1 -> 1040-NR (same wiring as 1040)
    FormWire("1040-Schedule-1", "10", "1040-NR", "schedule_1_additional_income"),
    FormWire("1040-Schedule-1", "26", "1040-NR", "schedule_1_adjustments"),

    # Schedule 2 -> 1040-NR
    FormWire("1040-Schedule-2", "21", "1040-NR", "schedule_2_additional_taxes"),

    # Schedule 3 -> 1040-NR
    FormWire("1040-Schedule-3", "8", "1040-NR", "schedule_3_nonrefundable_credits"),
    FormWire("1040-Schedule-3", "15", "1040-NR", "schedule_3_refundable_credits"),

    # Form 8995 -> 1040-NR
    FormWire("8995", "15", "1040-NR", "qbi_deduction"),
    FormWire("8995-A", "26", "1040-NR", "qbi_deduction"),

    # Schedule D -> 1040-NR
    FormWire("1040-Schedule-D", "16", "1040-NR", "capital_gain_or_loss"),

    # Schedule E -> Schedule 1 (as list item)
    FormWire(
        "1040-Schedule-E", "21", "1040-Schedule-1", "additional_income_items",
        target_is_list_item=True, item_description="Rental real estate income or loss",
    ),

    # Form 8949 -> Schedule D (as list items)
    FormWire(
        "8949", "short_gain", "1040-Schedule-D", "short_term_totals",
        target_is_list_item=True, item_description="Form 8949 short-term totals",
    ),
    FormWire(
        "8949", "long_gain", "1040-Schedule-D", "long_term_totals",
        target_is_list_item=True, item_description="Form 8949 long-term totals",
    ),

    # AGI-dependent forms.  AGI is computed from the SAME source values
    # that feed 1040, so these forms can be built in parallel with or
    # before the final 1040.  The wires below document the data origin
    # but are NOT treated as hard ordering dependencies to avoid false
    # cycles (1040 needs Schedule A, Schedule A needs AGI from 1040).
    # Agents should compute AGI independently for these forms.
    #
    # These wires use target_is_list_item=False (default) but are
    # annotated so the dependency resolver can skip the 1040 source
    # when computing build order — see _AGI_DOWNSTREAM_TARGETS below.
    FormWire("1040", "11", "1040-Schedule-A", "agi", notes="AGI; not a hard ordering dependency"),
    FormWire("1040", "11", "2441", "agi", notes="AGI; not a hard ordering dependency"),
    FormWire("1040", "11", "8863", "modified_agi", notes="AGI; not a hard ordering dependency"),
    FormWire("1040", "11", "1040-Schedule-8812", "modified_agi", notes="AGI; not a hard ordering dependency"),
    FormWire("1040", "11", "1040-Schedule-EIC", "agi", notes="AGI; not a hard ordering dependency"),
    FormWire("1040", "11", "1040-Schedule-1-A", "modified_agi_base", notes="AGI; not a hard ordering dependency"),

    # Form 8889 -> Schedule 1 adjustment
    FormWire(
        "8889", "13", "1040-Schedule-1", "adjustment_items",
        target_is_list_item=True, item_description="HSA deduction",
    ),

    # Form 8829 -> Schedule C (home office deduction feeds into expenses)
    FormWire(
        "8829", "35", "1040-Schedule-C", "expense_items",
        target_is_list_item=True, item_description="Home office deduction",
    ),

    # Form 2441 -> Schedule 3 (as list item)
    FormWire(
        "2441", "13", "1040-Schedule-3", "nonrefundable_credit_items",
        target_is_list_item=True, item_description="Child and dependent care credit",
    ),

    # Form 8863 -> Schedule 3 (as list item)
    FormWire(
        "8863", "30", "1040-Schedule-3", "nonrefundable_credit_items",
        target_is_list_item=True, item_description="Education credits",
    ),

    # Form 8962 -> Schedule 3 (as list item)
    FormWire(
        "8962", "26", "1040-Schedule-3", "payment_items",
        target_is_list_item=True, item_description="Net premium tax credit",
    ),

    # Schedule C / SE -> Form 8995 structured business assembly
    FormWire(
        "1040-Schedule-C", "31", "8995", "businesses",
        notes=(
            "Dependency only. Assemble business entries with src.qbi using "
            "Schedule C net profit, Schedule SE line 13, business identity, "
            "and any IRC 224 tip deduction."
        ),
    ),
    FormWire(
        "1040-Schedule-SE", "13", "8995", "businesses",
        notes=(
            "Dependency only. Deductible half SE tax reduces sole-proprietor "
            "QBI in src.qbi helper assembly."
        ),
    ),
    FormWire(
        "1040-Schedule-C", "31", "8995-A", "businesses",
        notes=(
            "Dependency only. Assemble business entries with src.qbi using "
            "Schedule C net profit, Schedule SE line 13, wage/property data, "
            "business identity, and any IRC 224 tip deduction."
        ),
    ),
    FormWire(
        "1040-Schedule-SE", "13", "8995-A", "businesses",
        notes=(
            "Dependency only. Deductible half SE tax reduces sole-proprietor "
            "QBI in src.qbi helper assembly."
        ),
    ),

    # Schedule D -> Form 8995 net_capital_gains
    FormWire("1040-Schedule-D", "16", "8995", "net_capital_gains"),
    FormWire("1040-Schedule-D", "16", "8995-A", "net_capital_gains"),
)


# ---------------------------------------------------------------------------
# Layer 2 — dependency graph utilities
# ---------------------------------------------------------------------------

def get_wires_for_target(target_form: str) -> list[FormWire]:
    """Return all wires that feed into the given target form."""
    return [w for w in FORM_WIRES if w.target_form == target_form]


def get_wires_from_source(source_form: str) -> list[FormWire]:
    """Return all wires that originate from the given source form."""
    return [w for w in FORM_WIRES if w.source_form == source_form]


_AGI_SOFT_DEPENDENCY_MARKER = "AGI; not a hard ordering dependency"


def get_form_dependencies(form_code: str) -> set[str]:
    """Return the set of forms that must be processed before *form_code*.

    Derived from FORM_WIRES: if any wire targets *form_code*, its source
    form is a dependency.  Wires annotated as soft AGI dependencies are
    excluded because AGI can be computed from the same upstream sources
    without waiting for the full 1040 processor to run.
    """
    return {
        w.source_form
        for w in FORM_WIRES
        if w.target_form == form_code
        and w.notes != _AGI_SOFT_DEPENDENCY_MARKER
    }


def get_all_dependencies(form_codes: list[str]) -> dict[str, set[str]]:
    """Return dependency sets for every form in *form_codes*, limited to
    forms within the provided set."""
    code_set = set(form_codes)
    return {
        fc: get_form_dependencies(fc) & code_set
        for fc in form_codes
    }


def get_build_order(form_codes: list[str]) -> list[str]:
    """Return a topologically sorted build order for the given forms.

    Forms with no intra-set dependencies come first.  Raises
    ``ValueError`` on cyclic dependencies.
    """
    deps = get_all_dependencies(form_codes)
    ordered: list[str] = []
    remaining = dict(deps)

    while remaining:
        ready = [fc for fc, dep_set in remaining.items() if not dep_set]
        if not ready:
            raise ValueError(
                f"Cyclic dependency among: {sorted(remaining)}"
            )
        ready.sort()
        ordered.extend(ready)
        for fc in ready:
            del remaining[fc]
        for dep_set in remaining.values():
            dep_set -= set(ready)

    return ordered


# ---------------------------------------------------------------------------
# Layer 1 — query utilities
# ---------------------------------------------------------------------------

def get_field_meta(form_code: str, field_name: str) -> FieldMeta | None:
    """Return metadata for a single field, or ``None`` if not catalogued."""
    form_fields = FIELD_METADATA.get(form_code, {})
    return form_fields.get(field_name)


def get_fields_by_role(
    form_code: str,
    role: FieldRole,
) -> dict[str, FieldMeta]:
    """Return all fields on *form_code* that have the given role."""
    return {
        name: meta
        for name, meta in FIELD_METADATA.get(form_code, {}).items()
        if meta.role == role
    }


def get_cross_form_fields(form_code: str) -> dict[str, FieldMeta]:
    """Shortcut: return all CROSS_FORM fields for a form."""
    return get_fields_by_role(form_code, FieldRole.CROSS_FORM)


def get_computed_input_fields(form_code: str) -> dict[str, FieldMeta]:
    """Shortcut: return all COMPUTED_INPUT fields for a form."""
    return get_fields_by_role(form_code, FieldRole.COMPUTED_INPUT)


def describe_field(form_code: str, field_name: str) -> str:
    """Return a human-readable summary of a field's role and wiring."""
    meta = get_field_meta(form_code, field_name)
    if meta is None:
        return f"{form_code}.{field_name}: no metadata catalogued"
    parts = [f"{form_code}.{field_name}: role={meta.role.value}"]
    if meta.description:
        parts.append(f"  description: {meta.description}")
    if meta.cross_form_ref:
        ref = meta.cross_form_ref
        parts.append(f"  source: {ref.source_form} line {ref.source_line}")
    for alt in meta.alternative_refs:
        parts.append(f"  alt source: {alt.source_form} line {alt.source_line}")
    if meta.notes:
        parts.append(f"  notes: {meta.notes}")
    return "\n".join(parts)
