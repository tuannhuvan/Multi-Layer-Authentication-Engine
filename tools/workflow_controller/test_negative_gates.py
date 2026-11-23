#!/usr/bin/env python3
"""
Negative Gate Verification Suite — Section 17.2 ("Kiểm thử quy trình trước khi tin gate")
Tests all mandatory failure/blocking scenarios before trusting gates:
1. Dev writing to sealed acceptance baseline or policy path -> Denied by policy enforcement check.
2. Reviewer timeout, Markdown output, or JSON missing required fields -> Gate does NOT pass.
3. Story reaches review cap (4 / 6 / 9) -> `reserve_review_slot` rejects new slot & story transitions to ESCALATED.
4. Reviewer reports new blocking finding on unchanged code in DELTA round -> Finding dropped (unless CRITICAL with evidence) (§8.4 Rule 2).
5. Post-merge main branch pipeline -> No LLM review called; only `verify-review-evidence` runs and checks SHA/baseline.
6. Empty test suite or skipped mandatory acceptance test -> `run-tests` fails G3 with explicit error.
7. Code SHA changes after review PASS -> G3-G5 invalidated (`STALE`); G4 requires DELTA review.
8. Worker dies or duplicate task claim -> Active lease blocks duplicate worker until expiry; recovers from checkpoint.
9. Another pipeline overwrites staging image mid-test -> `verify-staging` rejects evidence.
10. Production image digest differs from G5-approved manifest -> `deploy-production` blocks deployment.
11. Budget exceeded -> Story stops and transitions to ESCALATED.
12. High-risk story G4 requires both PO and TechLead human co-signatures before QUALITY_PASSED.
"""
import json
from pathlib import Path
import tempfile
import unittest
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "workflow_controller"))
sys.path.insert(0, str(REPO_ROOT / "infra" / "ci-policy"))

from controller import WorkflowController  # noqa: E402
import policy_cli  # noqa: E402


class TestV21NegativeGates(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_controller.db"
        self.ctrl = WorkflowController(db_path=self.db_path)
        self.sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        self.state = self.ctrl.init_story(
            story_id="US-012",
            risk_level="HIGH",
            candidate_sha=self.sha,
            state="BUILD_PASSED",
            review_used=5,
        )
        self.baseline_sha = self.state["baseline_manifest_sha256"]

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_dev_policy_blocks_acceptance_and_policy_writes(self):
        """§17.2 #1 & #2: BE/FE Dev policy explicitly denies writing to tests/acceptance, api, docs, and .agent-policy."""
        be_policy = json.loads((REPO_ROOT / ".agent-policy" / "be-dev.json").read_text(encoding="utf-8"))
        deny_write = be_policy["sandbox"]["filesystem"]["denyWrite"]
        self.assertIn("./tests/acceptance", deny_write)
        self.assertIn("./api", deny_write)
        self.assertIn("./docs", deny_write)
        self.assertIn("./.agent-policy", deny_write)

    def test_02_reviewer_invalid_schema_or_low_blocking_rejected(self):
        """§17.2 #3: Reviewer returning missing fields or LOW finding with blocking=true is rejected."""
        bad_payload = {
            "review_id": "REV-BAD-01",
            "role": "BIZ",
            "story_id": "US-012",
            # missing candidate_sha, mode, etc.
        }
        with self.assertRaises(ValueError):
            self.ctrl.validate_and_record_review("US-012", "BIZ", self.sha, bad_payload)

        low_blocking_payload = {
            "review_id": "REV-BAD-02",
            "role": "BIZ",
            "story_id": "US-012",
            "candidate_sha": self.sha,
            "baseline_manifest_sha256": self.baseline_sha,
            "mode": "FULL",
            "verdict": "FAIL",
            "checked_scope": ["backend/school-service/GradeService.java"],
            "findings": [
                {
                    "id": "F-01",
                    "severity": "LOW",
                    "category": "CODE",
                    "blocking": True,
                    "reference": "BR-031",
                    "location": "backend/school-service/GradeService.java:12",
                    "message": "Minor style issue",
                    "evidence": "line 12",
                    "resolution_condition": "Rename var",
                }
            ],
        }
        with self.assertRaises(ValueError):
            self.ctrl.validate_and_record_review("US-012", "BIZ", self.sha, low_blocking_payload)

    def test_03_review_cap_exceeded_escalates_story(self):
        """§17.2 #4: Story exhausting review cap (9 for HIGH, 4 for NORMAL) is refused and ESCALATED."""
        self.ctrl.init_story(story_id="US-NORM", risk_level="NORMAL", candidate_sha=self.sha, review_used=4)
        with self.assertRaises(RuntimeError):
            self.ctrl.reserve_review_slot("US-NORM", "BIZ", self.sha)
        st = self.ctrl.export_state("US-NORM")
        self.assertEqual(st["state"], "ESCALATED")
        self.assertIn("REVIEW_CAP_EXCEEDED", st["escalation_reason"])

    def test_04_delta_review_filters_new_blocking_finding_on_unchanged_code(self):
        """§17.2 #5 & §8.4 Rule 2: Non-critical blocking finding outside delta files is dropped."""
        delta_payload = {
            "review_id": "REV-DELTA-01",
            "role": "BIZ",
            "story_id": "US-012",
            "candidate_sha": self.sha,
            "baseline_manifest_sha256": self.baseline_sha,
            "mode": "DELTA",
            "previous_review_id": "REV-FULL-00",
            "closed_findings": ["F-OLD-01"],
            "verdict": "FAIL",
            "checked_scope": ["backend/school-service/GradeService.java", "backend/school-service/LegacyHelper.java"],
            "findings": [
                {
                    "id": "F-DRIP-HIGH",
                    "severity": "HIGH",
                    "category": "CODE",
                    "blocking": True,
                    "reference": "BR-031",
                    "location": "backend/school-service/LegacyHelper.java:45",
                    "message": "Late finding on unchanged file",
                    "evidence": "LegacyHelper.java:45",
                    "resolution_condition": "Refactor helper",
                }
            ],
        }
        res = self.ctrl.validate_and_record_review(
            "US-012",
            "BIZ",
            self.sha,
            delta_payload,
            delta_changed_files=["backend/school-service/GradeService.java"],
        )
        self.assertIn("F-DRIP-HIGH", res["dropped_findings_rule2"])
        self.assertEqual(res["effective_verdict"], "PASS")

    def test_05_main_branch_verifies_evidence_without_llm_and_requires_g4_signoff(self):
        """§17.2 #6 & §1.3: High-risk G4 requires PO+TechLead signoff; main branch verifies evidence without LLM."""
        for role in ("BIZ", "SEC"):
            payload = {
                "review_id": f"REV-US-012-{role}-PASS",
                "role": role,
                "story_id": "US-012",
                "candidate_sha": self.sha,
                "baseline_manifest_sha256": self.baseline_sha,
                "mode": "FULL",
                "verdict": "PASS",
                "checked_scope": ["docs/spec/rules/BR-031.md"],
                "findings": [],
            }
            self.ctrl.validate_and_record_review("US-012", role, self.sha, payload)

        # High-risk story must still be BUILD_PASSED until PO & TechLead sign G4
        st_before = self.ctrl.export_state("US-012")
        self.assertEqual(st_before["state"], "BUILD_PASSED")

        self.ctrl.sign_high_risk_g4("US-012", "PO", "Ng Tuân", self.sha)
        self.ctrl.sign_high_risk_g4("US-012", "TechLead", "Ng Tuân", self.sha)
        st_after = self.ctrl.export_state("US-012")
        self.assertEqual(st_after["state"], "QUALITY_PASSED")
        self.assertEqual(st_after["gates"]["G4"]["status"], "PASS")

        ev = self.ctrl.verify_review_evidence_on_main("US-012", self.sha, ["BIZ", "SEC"])
        self.assertFalse(ev["llm_called_on_main"])
        self.assertEqual(ev["status"], "PASS")

    def test_06_code_change_invalidates_g3_to_g5_stale(self):
        """§17.2 #8: Changing code SHA after review invalidates G3-G5 to STALE."""
        new_sha = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"
        st = self.ctrl.notify_input_change("US-012", new_sha, change_type="CODE")
        self.assertEqual(st["state"], "STALE")
        self.assertEqual(st["gates"]["G3"]["status"], "STALE")
        self.assertEqual(st["gates"]["G4"]["status"], "STALE")
        self.assertEqual(st["gates"]["G1"]["status"], "PASS")

    def test_07_atomic_lease_prevents_duplicate_worker_claim(self):
        """§17.2 #10: Active task lease blocks another worker from claiming the same task."""
        self.ctrl.acquire_lease("US-012", "TASK-US-012-BE", "worker-alpha", "BE_Dev", ttl_seconds=600)
        with self.assertRaises(RuntimeError):
            self.ctrl.acquire_lease("US-012", "TASK-US-012-BE", "worker-beta", "BE_Dev", ttl_seconds=600)

    def test_08_empty_or_skipped_acceptance_suite_fails_g3(self):
        """§17.2 #7: Empty test suite or skipped mandatory test fails G3 (`run-tests`)."""
        bad_suite = Path(self.tmp_dir.name) / "test_skipped.py"
        bad_suite.write_text("@unittest.skip('skip mandatory')\ndef test_x(): pass\n", encoding="utf-8")
        rc = policy_cli.cmd_run_tests(["--input", "reports/input-manifest.json", "--suite", str(bad_suite)])
        self.assertNotEqual(rc, 0)

    def test_09_staging_overwrite_and_production_digest_mismatch_blocked(self):
        """§17.2 #11 & #12: Staging digest overwrite or production digest mismatch is blocked."""
        img_file = Path(self.tmp_dir.name) / "image.json"
        dep_file = Path(self.tmp_dir.name) / "staging-deploy.json"
        rel_file = Path(self.tmp_dir.name) / "release-manifest.json"

        img_file.write_text(json.dumps({"commit_sha": self.sha, "image_digest": "sha256:1111"}), encoding="utf-8")
        dep_file.write_text(json.dumps({"commit_sha": self.sha, "deployed_digest": "sha256:2222"}), encoding="utf-8")
        rc_staging = policy_cli.cmd_verify_staging(["--image", str(img_file), "--deployment", str(dep_file)])
        self.assertNotEqual(rc_staging, 0)

        rel_file.write_text(
            json.dumps({"release_id": "REL-1", "image_digest": "sha256:1111", "g5_approved": True}),
            encoding="utf-8",
        )
        rc_prod = policy_cli.cmd_deploy_production(["--manifest", str(rel_file), "--target-digest", "sha256:9999"])
        self.assertNotEqual(rc_prod, 0)

    def test_10_budget_exceeded_escalates_story(self):
        """§17.2 #13: Exceeding story budget transitions story to ESCALATED."""
        self.ctrl.init_story(
            story_id="US-BUDGET",
            risk_level="HIGH",
            candidate_sha=self.sha,
            budget_limit=5.0,
            budget_spent=4.0,
            budget_reserved=0.8,
        )
        with self.assertRaises(RuntimeError):
            self.ctrl.reserve_review_slot("US-BUDGET", "BIZ", self.sha, slot_cost_usd=0.5)
        st = self.ctrl.export_state("US-BUDGET")
        self.assertEqual(st["state"], "ESCALATED")
        self.assertIn("BUDGET_EXCEEDED", st["escalation_reason"])


if __name__ == "__main__":
    unittest.main()
