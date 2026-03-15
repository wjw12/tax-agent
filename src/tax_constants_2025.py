"""Structured 2025 tax constants and routing helpers."""

from __future__ import annotations

from decimal import Decimal


STANDARD_DEDUCTION_2025 = {
    "single": Decimal("15750"),
    "married_filing_separately": Decimal("15750"),
    "married_filing_jointly": Decimal("31500"),
    "qualifying_surviving_spouse": Decimal("31500"),
    "head_of_household": Decimal("23625"),
}


SCHEDULE_1A_2025 = {
    "qualified_tips": {
        "cap": Decimal("25000"),
        "phaseout_threshold": {
            "married_filing_jointly": Decimal("300000"),
            "other": Decimal("150000"),
        },
        "phaseout_per_1000": Decimal("100"),
    },
    "qualified_overtime": {
        "cap": {
            "married_filing_jointly": Decimal("25000"),
            "other": Decimal("12500"),
        },
        "phaseout_threshold": {
            "married_filing_jointly": Decimal("300000"),
            "other": Decimal("150000"),
        },
        "phaseout_per_1000": Decimal("100"),
    },
    "qualified_passenger_vehicle_loan_interest": {
        "cap": Decimal("10000"),
        "phaseout_threshold": {
            "married_filing_jointly": Decimal("200000"),
            "other": Decimal("100000"),
        },
        "phaseout_per_1000_ceiling": Decimal("200"),
        "vin_required": True,
    },
    "enhanced_senior_deduction": {
        "amount_per_eligible_person": Decimal("6000"),
        "phaseout_threshold": {
            "married_filing_jointly": Decimal("150000"),
            "other": Decimal("75000"),
        },
        "phaseout_rate": Decimal("0.06"),
    },
}


SALT_2025 = {
    "base_cap": {
        "married_filing_separately": Decimal("20000"),
        "other": Decimal("40000"),
    },
    "phaseout_start_magi": {
        "married_filing_separately": Decimal("250000"),
        "other": Decimal("500000"),
    },
    "floor_cap": {
        "married_filing_separately": Decimal("5000"),
        "other": Decimal("10000"),
    },
}


CHILD_CREDITS_2025 = {
    "child_tax_credit_per_child": Decimal("2200"),
    "additional_child_tax_credit_per_child_max": Decimal("1700"),
    "other_dependent_credit_per_dependent": Decimal("500"),
    "phaseout_threshold": {
        "married_filing_jointly": Decimal("400000"),
        "other": Decimal("200000"),
    },
    "ctc_actc_valid_ssn_required_by_due_date": True,
}


QBI_2025 = {
    "form_8995_taxable_income_threshold": {
        "married_filing_jointly": Decimal("394600"),
        "other": Decimal("197300"),
    },
    "exclude_irc_224_qualified_tips_from_qbi": True,
}


FORM_8962_2025 = {
    "federal_poverty_line_table_year": 2024,
    "coverage_month_definition_changed": True,
}


HSA_2025 = {
    "self_only_hdhp_limit": Decimal("4300"),
    "family_hdhp_limit": Decimal("8550"),
    "catch_up_age": 55,
    "catch_up_amount": Decimal("1000"),
}


DEPENDENT_CARE_2025 = {
    "expense_cap_one_person": Decimal("3000"),
    "expense_cap_two_or_more": Decimal("6000"),
    "dependent_care_assistance_exclusion": {
        "married_filing_separately": Decimal("2500"),
        "other": Decimal("5000"),
    },
}


EDUCATION_CREDITS_2025 = {
    "aotc": {
        "first_expense_tier": Decimal("2000"),
        "second_expense_tier": Decimal("2000"),
        "second_tier_rate": Decimal("0.25"),
        "max_credit_per_student": Decimal("2500"),
        "phaseout": {
            "married_filing_jointly": {
                "start": Decimal("160000"),
                "end": Decimal("180000"),
            },
            "other": {
                "start": Decimal("80000"),
                "end": Decimal("90000"),
            },
        },
    },
    "llc": {
        "expense_cap_per_return": Decimal("10000"),
        "rate": Decimal("0.20"),
        "max_credit_per_return": Decimal("2000"),
        "phaseout": {
            "married_filing_jointly": {
                "start": Decimal("160000"),
                "end": Decimal("180000"),
            },
            "other": {
                "start": Decimal("80000"),
                "end": Decimal("90000"),
            },
        },
    },
}


SELF_EMPLOYMENT_TAX_2025 = {
    "earnings_factor": Decimal("0.9235"),
    "tax_rate": Decimal("0.153"),
    "deductible_fraction": Decimal("0.5"),
}


SCHEDULE_A_2025 = {
    "medical_expense_floor_rate": Decimal("0.075"),
}


CAPITAL_LOSS_2025 = {
    "max_deduction": Decimal("3000"),
}


SCHEDULE_C_2025 = {
    "business_mileage_rate": Decimal("0.70"),
}


SECTION_179_2025 = {
    "max_deduction": Decimal("2500000"),
    "phaseout_start": Decimal("4000000"),
    "suv_cap": Decimal("31300"),
}


def salt_cap_for_filing_status(filing_status: str) -> Decimal:
    bucket = "married_filing_separately" if filing_status == "married_filing_separately" else "other"
    return SALT_2025["base_cap"][bucket]


def filing_status_bucket(filing_status: str) -> str:
    return "married_filing_jointly" if filing_status == "married_filing_jointly" else "other"


def schedule_1a_threshold(section_key: str, filing_status: str) -> Decimal:
    section = SCHEDULE_1A_2025[section_key]
    return section["phaseout_threshold"][filing_status_bucket(filing_status)]


def qbi_form_8995_threshold(filing_status: str) -> Decimal:
    return QBI_2025["form_8995_taxable_income_threshold"][filing_status_bucket(filing_status)]


def education_credit_phaseout(credit_key: str, filing_status: str) -> dict[str, Decimal]:
    return EDUCATION_CREDITS_2025[credit_key]["phaseout"][filing_status_bucket(filing_status)]
