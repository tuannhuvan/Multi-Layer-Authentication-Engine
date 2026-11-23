#!/usr/bin/env python3
"""
Sealed Acceptance Test Suite for US-012 (Baseline TEST-US-012-004).
 Policy (§11, §14.2, §17.2):
- Must NOT be empty.
- Must NOT skip mandatory test cases.
- Verifies Golden Dataset, Anti-IDOR unit scope, ACR S3 Step-up, and Exempt weight=0.
"""
import csv
import json
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "mocker"))

from contract_mocker import (  # noqa: E402
    MOCK_DB,
    calculate_grade,
    sign_approval_s3,
    verify_unit_scope_and_acr,
)


class TestUS012Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden_path = REPO_ROOT / "docs" / "spec" / "golden" / "grade_calculation_golden.csv"
        cls.fixture_path = REPO_ROOT / "tests" / "fixtures" / "us012_fixtures.json"
        assert cls.golden_path.exists(), f"Missing golden dataset: {cls.golden_path}"
        assert cls.fixture_path.exists(), f"Missing fixture: {cls.fixture_path}"
        cls.fixtures = json.loads(cls.fixture_path.read_text(encoding="utf-8"))

    def test_ac012_01_golden_calculation(self):
        """AC-012-01: Verify all golden CSV records against BR-031 HALF_UP rounding and rank rules."""
        with self.golden_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 5, "Golden dataset must contain at least 5 reference cases")
        for row in rows:
            result = calculate_grade(
                {
                    "student_code": row["student_code"],
                    "class_id": row["class_id"],
                    "tx1": float(row["tx1"]),
                    "tx2": float(row["tx2"]),
                    "exempt_tx2": row["exempt_tx2"].lower() == "true",
                    "midterm": float(row["midterm"]),
                    "final_exam": float(row["final_exam"]),
                }
            )
            self.assertEqual(result["average_score"], float(row["expected_avg"]), f"Failed avg on {row['case_id']}")
            self.assertEqual(result["academic_rank"], row["expected_rank"], f"Failed rank on {row['case_id']}")

    def test_ac012_02_anti_idor_unit_scope(self):
        """AC-012-02: Teacher assigned to 10A1 must be blocked from updating 10A2 with RFC 9457 traceId."""
        ok, problem = verify_unit_scope_and_acr("10A2", "10A1", "S2")
        self.assertFalse(ok)
        self.assertIsNotNone(problem)
        self.assertEqual(problem["status"], 403)
        self.assertEqual(problem["error_code"], "UNIT_SCOPE_FORBIDDEN")
        self.assertTrue(problem["traceId"].startswith("tr-"))

        ok_valid, problem_valid = verify_unit_scope_and_acr("10A1", "10A1", "S2")
        self.assertTrue(ok_valid)
        self.assertIsNone(problem_valid)

    def test_ac012_03_require_acr_s3_signature(self):
        """AC-012-03: Post-lock grade change approval requires ACR=S3 digital signature."""
        status_s2, body_s2 = sign_approval_s3("CR-GRADE-001", "S2")
        self.assertEqual(status_s2, 403)
        self.assertEqual(body_s2["error_code"], "STEP_UP_S3_REQUIRED")
        self.assertIn("traceId", body_s2)

        status_s3, body_s3 = sign_approval_s3("CR-GRADE-001", "S3")
        self.assertEqual(status_s3, 200)
        self.assertEqual(body_s3["status"], "APPROVED")
        self.assertEqual(body_s3["acr_verified"], "S3")

    def test_ac012_04_exempt_zero_weight(self):
        """AC-012-04: Exempt component column reduces denominator without division error."""
        result = calculate_grade(
            {
                "student_code": "HS004",
                "class_id": "10A1",
                "tx1": 8.0,
                "tx2": 0.0,
                "exempt_tx2": True,
                "midterm": 8.0,
                "final_exam": 8.0,
            }
        )
        self.assertEqual(result["average_score"], 8.0)
        self.assertEqual(result["academic_rank"], "GIOI")

    def test_ac012_05_worm_hmac_chain_integrity(self):
        """SoD-03 (PH6): Verify WORM Audit Log HMAC-SHA256 hash chain links prev_hmac_hash -> entry_hmac_hash."""
        self.assertGreaterEqual(len(MOCK_DB.worm_logs), 2)
        self.assertEqual(MOCK_DB.worm_logs[0]["prev_hmac_hash"], "0" * 64)
        self.assertEqual(MOCK_DB.worm_logs[1]["prev_hmac_hash"], MOCK_DB.worm_logs[0]["entry_hmac_hash"])
        rec3 = MOCK_DB.append_worm_log(
            actor_user_id="22222222-3333-4444-5555-666666666602",
            actor_role="BOARD",
            acr_level="S3",
            subsystem_code="PH4_EXAM",
            use_case_code="UC-BRD-06",
            action_type="UNLOCK_MAKER_CHECKER_24H",
            target_table="grade_appeals",
            target_record_id="GA-2026-089",
            after_state={"window_hours": 24},
        )
        self.assertEqual(rec3["prev_hmac_hash"], MOCK_DB.worm_logs[1]["entry_hmac_hash"])


if __name__ == "__main__":
    unittest.main()
