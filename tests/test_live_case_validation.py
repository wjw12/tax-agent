from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.case_artifacts import write_json_artifact
from src.input_loader import load_form_audit_sidecar
from src.input_loader import load_form_input
from src.live_case_builder import LiveCaseBuilder


class LiveCaseValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(dir="/home/appuser/tax/workspace/cases")
        self.case_root = Path(self.temp_dir.name)
        self.input_dir = self.case_root / "data" / "input" / "2025"
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.builder = LiveCaseBuilder(self.case_root, tax_year=2025)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_form(self, payload: dict, sidecar: dict) -> Path:
        result = self.builder.write_form_bundle(payload, sidecar)
        return result.payload_path

    def _base_payload(self) -> dict:
        return {
            "form_code": "1040-NR",
            "tax_year": 2025,
            "residency_status": "nonresident_alien",
            "filing_status": "single",
            "taxpayer": {
                "first_name": "Elena",
                "last_name": "Kovacs",
                "ssn": None,
                "identifying_number": "900-70-1000",
                "address": {
                    "line1": "14 Birch Lane",
                    "line2": None,
                    "city": "Boston",
                    "state": "MA",
                    "postal_code": "02110",
                    "country": "Hungary",
                },
                "date_of_birth": None,
                "occupation": None,
            },
            "dependents": [],
            "digital_assets": False,
            "country_of_citizenship": "Hungary",
            "country_of_tax_residence": "Hungary",
            "visa_type": "F-1",
            "days_present_in_us": 180,
            "claims_treaty_benefits": True,
            "treaty_country": "Hungary",
            "has_dual_status": False,
            "qualifying_person_name": "",
            "wages": "28600.00",
            "taxable_interest": "0",
            "ordinary_dividends": "0",
            "qualified_dividends": "0",
            "ira_distributions": "0",
            "taxable_ira_distributions": "0",
            "pension_annuity_income": "0",
            "taxable_pension_annuity_income": "0",
            "capital_gain_or_loss": "0",
            "schedule_1_additional_income": "0",
            "treaty_exempt_income": "5000.00",
            "schedule_1_adjustments": "0",
            "itemized_deductions": "0",
            "standard_deduction": "0",
            "qbi_deduction": "0",
            "estate_or_trust_exemption": "0",
            "schedule_1a_additional_deductions": "0",
            "tax_before_credits": "3193.50",
            "schedule_2_additional_taxes": "0",
            "child_tax_credit_or_other_dependent_credit": "0",
            "schedule_3_nonrefundable_credits": "0",
            "nec_tax": "0",
            "other_taxes": "0",
            "transportation_tax": "0",
            "withholding_w2": "0",
            "withholding_1099": "0",
            "withholding_other_forms": "0",
            "withholding_8805": "0",
            "withholding_8288a": "0",
            "withholding_1042s": "3150.00",
            "estimated_tax_payments": "0",
            "additional_child_tax_credit": "0",
            "form_1040c_credit": "0",
            "refundable_adoption_credit": "0",
            "schedule_3_refundable_credits": "0",
            "amount_applied_to_next_year": "0",
        }

    def _base_sidecar(self) -> dict:
        return {
            "schema_version": "1.0",
            "form_code": "1040-NR",
            "tax_year": 2025,
            "status": "accepted",
            "sources": [
                {
                    "output_key": "wages",
                    "value": "28600",
                    "file": "1042-s-university.pdf",
                    "page": 1,
                    "locator": "Gross income paid",
                    "extractor": "synthetic-case",
                    "router_confidence": "high",
                },
                {
                    "output_key": "withholding_1042s",
                    "value": "3150",
                    "file": "1042-s-university.pdf",
                    "page": 1,
                    "locator": "Federal tax withheld",
                    "extractor": "synthetic-case",
                    "router_confidence": "high",
                },
                {
                    "output_key": "treaty_exempt_income",
                    "value": "5000",
                    "file": "1042-s-university.pdf",
                    "page": 1,
                    "locator": "Treaty exemption amount",
                    "extractor": "synthetic-case",
                    "router_confidence": "high",
                },
            ],
            "computations": [
                {
                    "output_key": "tax_before_credits",
                    "inputs": ["wages"],
                    "python_expression": "compute_ordinary_income_tax_2025('single', Decimal('28600'))",
                    "result": "3193.50",
                }
            ],
            "issues": [],
            "form_path": str(self.input_dir / "1040-nr.json"),
        }

    def test_rejects_invalid_audit_sidecar_shape(self) -> None:
        payload_path = self._write_form(self._base_payload(), self._base_sidecar())
        path = self.input_dir / "1040-nr.audit.json"
        path.write_text(
            '{\n'
            '  "schema_version": "1.0",\n'
            '  "form_code": "1040-NR",\n'
            '  "tax_year": 2025,\n'
            '  "status": "accepted",\n'
            '  "sources": ["1042-s-university.pdf"],\n'
            '  "computations": ["tax"],\n'
            '  "issues": []\n'
            '}\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Invalid audit sidecar"):
            load_form_input(payload_path)

    def test_rejects_wages_netted_against_treaty_exemption(self) -> None:
        bad_payload = self._base_payload()
        bad_payload["wages"] = "23600"
        bad_payload["tax_before_credits"] = "2593.50"
        payload_path = self._write_form(bad_payload, self._base_sidecar())

        with self.assertRaisesRegex(ValueError, "wages expected"):
            load_form_input(payload_path)

    def test_accepts_matching_payload_and_sidecar(self) -> None:
        payload_path = self._write_form(self._base_payload(), self._base_sidecar())

        parsed = load_form_input(payload_path)

        self.assertEqual(str(parsed.wages), "28600.00")
        self.assertEqual(str(parsed.tax_before_credits), "3193.50")

    def test_rejects_direct_live_case_payload_write(self) -> None:
        path = self.input_dir / "1040-nr.json"

        with self.assertRaisesRegex(ValueError, "LiveCaseBuilder"):
            write_json_artifact(path, self._base_payload())

    def test_builder_accepts_runtime_extraction_result(self) -> None:
        runtime_result = {
            **self._base_sidecar(),
            "form_payload": self._base_payload(),
        }

        result = self.builder.write_runtime_result(runtime_result)
        sidecar = load_form_audit_sidecar(result.audit_path)
        parsed = load_form_input(result.payload_path)

        self.assertEqual(sidecar.form_code, "1040-NR")
        self.assertEqual(sidecar.status, "accepted")
        self.assertEqual(str(parsed.wages), "28600.00")

    def test_builder_can_update_existing_audit_sidecar(self) -> None:
        payload_path = self._write_form(self._base_payload(), self._base_sidecar())

        self.builder.update_audit_sidecar(
            "1040-NR",
            status="needs_review",
            issues=[
                {
                    "code": "manual_tax_rule_review",
                    "severity": "medium",
                    "message": "Review needed",
                    "related_keys": ["tax_before_credits"],
                }
            ],
        )

        sidecar = load_form_audit_sidecar(self.input_dir / "1040-nr.audit.json")
        parsed = load_form_input(payload_path)

        self.assertEqual(sidecar.status, "needs_review")
        self.assertEqual(sidecar.issues[0].code, "manual_tax_rule_review")
        self.assertEqual(len(sidecar.sources), 3)
        self.assertEqual(str(parsed.tax_before_credits), "3193.50")


if __name__ == "__main__":
    unittest.main()
