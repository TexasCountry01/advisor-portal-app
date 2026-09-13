"""
Tests for the Fact Finder Data Contract schema (Phase 1 of the PDF modernization plan —
see docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md).

These tests validate the schema itself against a realistic sample payload built from
verified field names in benefits-software's EmployeeRepository.php / EmployeeController.php.
They do not touch benefits-software, any live calculation, or any database model.
"""
from django.test import SimpleTestCase

from cases.fact_finder_data_contract import FactFinderDataContractSerializer, SCHEMA_VERSION


def _sample_contract():
    """A realistic, schema-valid sample instance."""
    return {
        "schema_version": SCHEMA_VERSION,
        "employee_id": 12345,
        "generated_at": "2026-09-12T00:00:00Z",
        "system": {
            "system_type": "FERS",
            "retirement_type": "Deferred",
            "birth_year": 1968,
        },
        "pension": {
            "scenarios": [
                {
                    "scenario_number": 1,
                    "retirement_date": "2026-12-31",
                    "gross_annual_pension": "48210.00",
                    "first_pension_mra10_penalty": "0.00",
                    "months_under_62": 0,
                    "multiplier": "1.0000",
                    "early_out_penalty": "0.00",
                    "csrs_offset_penalty": "0.00",
                },
            ],
            "non_deduction_penalty": "0.00",
            "refunded_penalty": "0.00",
            "wep_penalty": "0.00",
        },
        "fegli": {
            "current_fegli": {
                "basic": True,
                "optionA": True,
                "optionB": 3,
                "optionC": 2,
                "optionC_spouse": True,
                "optionC_dependent": False,
            },
            "is_married": True,
            "has_dependents": False,
            "fegli_arr": [
                {
                    "age": 58,
                    "years_in_retirement": 0,
                    "annual_sal": "95000.00",
                    "basic_coverage": "95000.00",
                    "optionA_coverage": "10000.00",
                    "optionB_coverage": "285000.00",
                    "optionC_coverage": "10000.00",
                    "total_coverage": "400000.00",
                    "totalBiWeekly": "42.10",
                    "totalMonthly": "91.22",
                    "totalYearly": "1094.60",
                    "runningTotalCost": "1094.60",
                },
            ],
            "fegli_all_scenarios": [],
        },
        "social_security": {
            "ss_cola": "2.500",
            "ss_earned_income_limit": "23400.00",
            "ss_years_earning": 22,
            "ss_details": [
                {
                    "years_in_ret": 1,
                    "age": 63,
                    "monthly_pension": "4020.00",
                    "fers_srs": "900.00",
                    "ss_benefits": "0.00",
                    "total": "4920.00",
                },
            ],
        },
        "tsp": {
            "funds": [
                {"fund_code": "GFund", "balance": "102000.00", "allocation_pct": "20.00"},
                {"fund_code": "CFund", "balance": "250000.00", "allocation_pct": "40.00"},
                {"fund_code": "L2050", "balance": "160340.00", "allocation_pct": "40.00"},
            ],
            "agency_percentage": "4.000",
            "agency_contribution": "3800.00",
            "employee_contribution": "4750.00",
            "sal_percentage_in_contri": "5.000",
            "max_agency_contribution": "4750.00",
        },
        "computed_flags": {
            "is_fers_or_transfers": True,
            "is_csrs_or_csrs_offset": False,
            "is_deferred_retirement": True,
            "is_wep_applicable": False,
            "is_gpo_applicable": False,
            "hit_full_tsp_match": True,
        },
    }


class FactFinderDataContractSchemaTests(SimpleTestCase):
    def test_valid_sample_passes(self):
        serializer = FactFinderDataContractSerializer(data=_sample_contract())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_fegli_arr_years_in_retirement_accepts_asterisk_marker(self):
        """Grounded in a real end-to-end validation finding (2026-09-12, case #42293):
        EmployeeRepository::getFegliReport() emits a literal '*' marker for
        years_in_retirement on at least one row (a footnote-style flag in the source
        table), not always a number. The contract must accept it faithfully."""
        payload = _sample_contract()
        payload["fegli"]["fegli_arr"][0]["years_in_retirement"] = "*"
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["fegli"]["fegli_arr"][0]["years_in_retirement"], "*")

    def test_fegli_arr_years_in_retirement_still_accepts_numeric_value(self):
        payload = _sample_contract()
        payload["fegli"]["fegli_arr"][0]["years_in_retirement"] = 5
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["fegli"]["fegli_arr"][0]["years_in_retirement"], "5")

    def test_wrong_schema_version_is_rejected(self):
        payload = _sample_contract()
        payload["schema_version"] = "2020.1"
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("schema_version", serializer.errors)

    def test_missing_required_nested_field_is_rejected(self):
        payload = _sample_contract()
        del payload["tsp"]["sal_percentage_in_contri"]
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("tsp", serializer.errors)

    def test_invalid_system_type_choice_is_rejected(self):
        payload = _sample_contract()
        payload["system"]["system_type"] = "NotARealSystem"
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("system", serializer.errors)

    def test_missing_computed_flags_is_rejected(self):
        payload = _sample_contract()
        del payload["computed_flags"]
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("computed_flags", serializer.errors)

    def test_missing_wep_flag_is_rejected(self):
        """is_wep_applicable is required — it's the exact compound condition
        (systemType in CSRS/CSRS Offset) and (SSYearsEarning < 30) currently
        hardcoded inline in the blade template's WEP sentence."""
        payload = _sample_contract()
        del payload["computed_flags"]["is_wep_applicable"]
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("computed_flags", serializer.errors)
        self.assertIn("is_wep_applicable", serializer.errors["computed_flags"])

    def test_ss_years_earning_is_optional(self):
        """ss_years_earning is an input feeding is_wep_applicable, not itself a
        required output — a contract producer may omit it once the flag is computed."""
        payload = _sample_contract()
        del payload["social_security"]["ss_years_earning"]
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_mra_year_and_month_accept_real_values(self):
        """Grounded in EmployeeRepository::getMinumumRetirementAge()['mra_year']/['mra_month']
        — added 2026-09-13 to support the real MRA paragraph's merge fields during content
        migration (docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md)."""
        payload = _sample_contract()
        payload["pension"]["mra_year"] = 56
        payload["pension"]["mra_month"] = 4
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["pension"]["mra_year"], 56)
        self.assertEqual(serializer.validated_data["pension"]["mra_month"], 4)

    def test_mra_year_and_month_accept_null(self):
        """getMinumumRetirementAge() returns '' for both when DateOfBirth is missing; the
        PHP builder coerces that to null rather than passing the raw empty string through."""
        payload = _sample_contract()
        payload["pension"]["mra_year"] = None
        payload["pension"]["mra_month"] = None
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["pension"]["mra_year"])

    def test_mra_year_and_month_are_optional_for_backward_compatibility(self):
        """Older golden-master fixtures captured before this field existed must still
        validate — mra_year/mra_month are required=False for exactly this reason."""
        payload = _sample_contract()
        serializer = FactFinderDataContractSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
