#!/usr/bin/env python3
"""
AI-Agent Workflow Controller MVP — V2.1 (Section 2.1, 2.3, 7, 8, 9, Appendix A, B, E)
Deterministic orchestrator using SQLite transaction state store:
- 10 primary states + 8 exception states (DRAFT -> ... -> RELEASED, STALE, BLOCKED, ESCALATED, etc.)
- Atomic task lease & heartbeat management
- Risk-based LLM review cap counter: NORMAL (2/4), MEDIUM (4/6), HIGH (5/9)
- Automatic FULL vs DELTA review selection (§8.3)
- Review output validator (`validate_review_payload`) with anti-drip rule (§8.4 Rule 2) & category routing (§7.3)
- High-risk G4 human co-signing (PO + Tech Lead) (§1.3, §6)
- Read-only state export to `.pipeline/state.json` (Appendix A)
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / ".pipeline" / "controller.db"
DEFAULT_STATE_EXPORT_PATH = REPO_ROOT / ".pipeline" / "state.json"
DEFAULT_BASELINE_MANIFEST_PATH = REPO_ROOT / ".pipeline" / "baseline-manifest.json"

PRIMARY_STATES = [
    "DRAFT",
    "SPEC_APPROVED",
    "DESIGN_APPROVED",
    "TEST_READY",
    "IMPLEMENTING",
    "BUILD_PASSED",
    "QUALITY_PASSED",
    "RELEASE_READY",
    "RELEASE_APPROVED",
    "RELEASED",
]

EXCEPTION_STATES = [
    "STALE",
    "BLOCKED",
    "CHANGE_REQUIRED",
    "RETRY_PENDING",
    "ESCALATED",
    "CANCELLED",
    "RELEASE_FAILED",
]

ALL_STATES = set(PRIMARY_STATES + EXCEPTION_STATES)

REVIEW_CAPS = {
    "NORMAL": {"base": 2, "max": 4, "full_rereview_max": 0, "delta_max": 2},
    "MEDIUM": {"base": 4, "max": 6, "full_rereview_max": 0, "delta_max": 2},
    "HIGH": {"base": 5, "max": 9, "full_rereview_max": 1, "delta_max": 3},
}

ERROR_ROUTING_TABLE = {
    "SPEC": {"target": "BA/P1 + PO", "action": "BLOCK_AND_OPEN_CR", "limit": "BY_CR"},
    "DESIGN": {"target": "Architect/P2", "action": "IMPACT_ANALYSIS_AND_UPDATE_BASELINE", "limit": "BY_CR"},
    "TEST": {"target": "Tester/P3", "action": "FIX_TEST_AND_REISSUE_BASELINE", "limit": 2},
    "CODE": {"target": "FE/BE/P4", "action": "ASSIGN_FIX_WITH_REPRO_TEST_AND_DELTA_REVIEW", "limit": 3},
    "INFRA": {"target": "DevOps", "action": "RETRY_INFRA_WITHOUT_REVIEW_COST", "limit": 2},
    "POLICY": {"target": "Responsible_Human", "action": "ESCALATED_NO_AUTO_PRIVILEGE_EXPANSION", "limit": 0},
}

SENSITIVE_HIGH_RISK_PATTERNS = [
    "security/",
    "db/migration/",
    "authenticator-service/",
    "api-gateway/",
    "grades/",
    ".agent-policy/",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_baseline_manifest(repo_root: Path = REPO_ROOT) -> dict:
    """Computes SHA-256 checksums of versioned sources of truth (§1.2 Rule 1)."""
    tracked = {
        "spec": {
            "id": "SPEC-003",
            "files": [
                "docs/spec/rules/BR-031.md",
                "docs/spec/stories/US-012.md",
                "docs/spec/golden/grade_calculation_golden.csv",
            ],
        },
        "contract": {
            "id": "API-002",
            "files": ["api/openapi.yaml"],
        },
        "test": {
            "id": "TEST-US-012-004",
            "files": [
                "tests/acceptance/test_us012_grades.py",
                "tests/fixtures/us012_fixtures.json",
                "tests/plans/US-012-test-plan.md",
            ],
        },
        "ui": {
            "id": "UI-002",
            "files": ["docs/design/ui-baseline.md"],
        },
        "policy": {
            "id": "POLICY-001",
            "files": [
                ".agent-policy/schemas/review.schema.json",
                ".agent-policy/schemas/change-request.schema.json",
                ".agent-policy/schemas/task-manifest.schema.json",
                ".agent-policy/be-dev.json",
                ".agent-policy/fe-dev.json",
                ".agent-policy/ba.json",
                ".agent-policy/architect.json",
                ".agent-policy/tester.json",
                ".agent-policy/devops.json",
                ".agent-policy/reviewer.json",
            ],
        },
    }

    manifest_entries = {}
    overall_hasher = hashlib.sha256()

    for domain, cfg in tracked.items():
        domain_hasher = hashlib.sha256()
        file_hashes = {}
        for rel in sorted(cfg["files"]):
            fp = repo_root / rel
            fhash = sha256_file(fp) if fp.exists() else "MISSING"
            file_hashes[rel] = fhash
            domain_hasher.update(f"{rel}:{fhash}\n".encode("utf-8"))
        domain_sha = domain_hasher.hexdigest()
        manifest_entries[domain] = {
            "baseline_id": cfg["id"],
            "sha256": domain_sha,
            "files": file_hashes,
        }
        overall_hasher.update(f"{domain}:{cfg['id']}:{domain_sha}\n".encode("utf-8"))

    return {
        "manifest_version": "V2.1",
        "generated_at": utc_now_iso(),
        "baseline_manifest_sha256": overall_hasher.hexdigest(),
        "baselines": manifest_entries,
    }


class WorkflowController:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            with conn:
                conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stories (
                    story_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    candidate_sha TEXT NOT NULL,
                    baselines_json TEXT NOT NULL,
                    baseline_manifest_sha256 TEXT NOT NULL,
                    active_run_id TEXT,
                    risk_level TEXT NOT NULL,
                    functional_attempts INTEGER NOT NULL DEFAULT 0,
                    infrastructure_attempts INTEGER NOT NULL DEFAULT 0,
                    review_limit INTEGER NOT NULL,
                    review_used INTEGER NOT NULL DEFAULT 0,
                    review_delta_used INTEGER NOT NULL DEFAULT 0,
                    review_full_rereview_used INTEGER NOT NULL DEFAULT 0,
                    last_reviewed_sha TEXT,
                    budget_currency TEXT NOT NULL DEFAULT 'USD',
                    budget_limit REAL NOT NULL DEFAULT 10.0,
                    budget_spent REAL NOT NULL DEFAULT 0.0,
                    budget_reserved REAL NOT NULL DEFAULT 0.0,
                    gates_json TEXT NOT NULL,
                    g4_signoffs_json TEXT NOT NULL DEFAULT '{}',
                    escalation_reason TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS leases (
                    task_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    leased_until TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_slots (
                    slot_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    candidate_sha TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    budget_usd REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    recorded_review_id TEXT
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    candidate_sha TEXT NOT NULL,
                    baseline_manifest_sha256 TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    checked_scope_json TEXT NOT NULL,
                    findings_json TEXT NOT NULL,
                    closed_findings_json TEXT NOT NULL,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_log (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def init_story(
        self,
        story_id: str,
        risk_level: str = "HIGH",
        candidate_sha: str = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        state: str = "BUILD_PASSED",
        budget_limit: float = 10.0,
        budget_spent: float = 3.25,
        budget_reserved: float = 1.5,
        review_used: int = 5,
        active_run_id: str = "RUN-US-012-P5-001",
        revision: int = 17,
    ) -> dict:
        if risk_level not in REVIEW_CAPS:
            raise ValueError(f"Invalid risk_level: {risk_level}")
        if state not in ALL_STATES:
            raise ValueError(f"Invalid state: {state}")

        manifest = compute_baseline_manifest()
        DEFAULT_BASELINE_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_BASELINE_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        baselines = {
            "spec": manifest["baselines"]["spec"]["baseline_id"],
            "contract": manifest["baselines"]["contract"]["baseline_id"],
            "test": manifest["baselines"]["test"]["baseline_id"],
            "ui": manifest["baselines"]["ui"]["baseline_id"],
            "policy": manifest["baselines"]["policy"]["baseline_id"],
        }
        gates = {
            "G1": {"status": "PASS", "evidence_id": "EV-G1-003"},
            "G2": {"status": "PASS", "evidence_id": "EV-G2-002"},
            "G3": {"status": "PASS", "evidence_id": "EV-G3-017", "candidate_sha": candidate_sha},
            "G4": {"status": "PENDING"},
            "G5": {"status": "PENDING"},
        }
        limit = REVIEW_CAPS[risk_level]["max"]
        now = utc_now_iso()

        with self._connect() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stories (
                        story_id, state, revision, candidate_sha, baselines_json,
                        baseline_manifest_sha256, active_run_id, risk_level,
                        functional_attempts, infrastructure_attempts,
                        review_limit, review_used, review_delta_used, review_full_rereview_used,
                        last_reviewed_sha, budget_currency, budget_limit, budget_spent, budget_reserved,
                        gates_json, g4_signoffs_json, escalation_reason, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?, '{}', NULL, ?)
                    """,
                    (
                        story_id,
                        state,
                        revision,
                        candidate_sha,
                        json.dumps(baselines),
                        manifest["baseline_manifest_sha256"],
                        active_run_id,
                        risk_level,
                        1,
                        0,
                        limit,
                        review_used,
                        0,
                        0,
                        candidate_sha,
                        budget_limit,
                        budget_spent,
                        budget_reserved,
                        json.dumps(gates),
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO event_log (story_id, event_type, from_state, to_state, actor, details_json, created_at)
                    VALUES (?, 'STORY_INITIALIZED', NULL, ?, 'Controller', ?, ?)
                    """,
                    (story_id, state, json.dumps({"risk_level": risk_level, "candidate_sha": candidate_sha}), now),
                )
        return self.export_state(story_id)

    def get_story_row(self, story_id: str) -> sqlite3.Row:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM stories WHERE story_id = ?", (story_id,)).fetchone()
            if not row:
                raise KeyError(f"Story '{story_id}' not found in Controller DB.")
            return row

    def export_state(self, story_id: str, out_path: Path = DEFAULT_STATE_EXPORT_PATH) -> dict:
        """Exports observational `.pipeline/state.json` matching Appendix A."""
        row = self.get_story_row(story_id)
        state_obj = {
            "story_id": row["story_id"],
            "state": row["state"],
            "revision": row["revision"],
            "candidate_sha": row["candidate_sha"],
            "baselines": json.loads(row["baselines_json"]),
            "baseline_manifest_sha256": row["baseline_manifest_sha256"],
            "active_run_id": row["active_run_id"],
            "risk_level": row["risk_level"],
            "functional_attempts": row["functional_attempts"],
            "infrastructure_attempts": row["infrastructure_attempts"],
            "review": {
                "limit": row["review_limit"],
                "used": row["review_used"],
                "delta_used": row["review_delta_used"],
                "full_rereview_used": row["review_full_rereview_used"],
                "last_reviewed_sha": row["last_reviewed_sha"],
            },
            "budget": {
                "currency": row["budget_currency"],
                "limit": row["budget_limit"],
                "spent": round(row["budget_spent"], 4),
                "reserved": round(row["budget_reserved"], 4),
            },
            "gates": json.loads(row["gates_json"]),
        }
        signoffs = json.loads(row["g4_signoffs_json"] or "{}")
        if signoffs:
            state_obj["g4_signoffs"] = signoffs
        if row["escalation_reason"]:
            state_obj["escalation_reason"] = row["escalation_reason"]

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(state_obj, indent=2, ensure_ascii=False), encoding="utf-8")
        return state_obj

    def evaluate_risk_escalation(self, story_id: str, changed_files: list[str]) -> str:
        """§11: Diff touching sensitive paths automatically escalates risk_level to HIGH."""
        row = self.get_story_row(story_id)
        current_risk = row["risk_level"]
        for fpath in changed_files:
            norm = fpath.replace("\\", "/")
            if any(pat in norm for pat in SENSITIVE_HIGH_RISK_PATTERNS):
                if current_risk != "HIGH":
                    with self._connect() as conn:
                        conn.execute(
                            "UPDATE stories SET risk_level = 'HIGH', review_limit = ?, revision = revision + 1, updated_at = ? WHERE story_id = ?",
                            (REVIEW_CAPS["HIGH"]["max"], utc_now_iso(), story_id),
                        )
                        conn.execute(
                            """
                            INSERT INTO event_log (story_id, event_type, from_state, to_state, actor, details_json, created_at)
                            VALUES (?, 'AUTO_RISK_ESCALATION', ?, ?, 'Controller', ?, ?)
                            """,
                            (
                                story_id,
                                row["state"],
                                row["state"],
                                json.dumps({"trigger_file": norm, "new_risk": "HIGH"}),
                                utc_now_iso(),
                            ),
                        )
                return "HIGH"
        return current_risk

    def acquire_lease(self, story_id: str, task_id: str, worker_id: str, role: str, ttl_seconds: int = 900) -> dict:
        """§7.2: Atomic task lease acquisition; rejects duplicate active lease unless expired."""
        now = datetime.now(timezone.utc)
        leased_until = (now + timedelta(seconds=ttl_seconds)).isoformat()
        run_id = f"RUN-{story_id}-{role.upper()}-{uuid.uuid4().hex[:6].upper()}"

        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM leases WHERE task_id = ?", (task_id,)).fetchone()
            if existing and existing["status"] == "ACTIVE":
                exp = datetime.fromisoformat(existing["leased_until"])
                if exp > now and existing["worker_id"] != worker_id:
                    raise RuntimeError(
                        f"Task '{task_id}' is currently leased by worker '{existing['worker_id']}' until {existing['leased_until']}."
                    )

            conn.execute(
                """
                INSERT OR REPLACE INTO leases (task_id, story_id, worker_id, role, run_id, leased_until, status)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (task_id, story_id, worker_id, role, run_id, leased_until),
            )
            conn.execute(
                "UPDATE stories SET active_run_id = ?, revision = revision + 1, updated_at = ? WHERE story_id = ?",
                (run_id, now.isoformat(), story_id),
            )
        self.export_state(story_id)
        return {"task_id": task_id, "story_id": story_id, "worker_id": worker_id, "run_id": run_id, "leased_until": leased_until}

    def notify_input_change(self, story_id: str, new_sha: str, change_type: str = "CODE") -> dict:
        """§9.2: Changing candidate SHA or baselines invalidates downstream gates (G3-G5) and sets state accordingly."""
        row = self.get_story_row(story_id)
        gates = json.loads(row["gates_json"])
        old_state = row["state"]

        if change_type == "CODE":
            for g in ("G3", "G4", "G5"):
                gates[g] = {"status": "STALE", "invalidated_by_sha": new_sha}
            new_state = "STALE"
        elif change_type in ("SPEC", "CONTRACT", "TEST"):
            for g in ("G1", "G2", "G3", "G4", "G5"):
                if change_type == "TEST" and g in ("G1", "G2"):
                    continue
                if change_type == "CONTRACT" and g == "G1":
                    continue
                gates[g] = {"status": "STALE", "invalidated_by": change_type}
            new_state = "STALE"
        else:
            raise ValueError(f"Unsupported change_type: {change_type}")

        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE stories
                SET state = ?, candidate_sha = ?, gates_json = ?, g4_signoffs_json = '{}',
                    revision = revision + 1, updated_at = ?
                WHERE story_id = ?
                """,
                (new_state, new_sha, json.dumps(gates), now, story_id),
            )
            conn.execute(
                """
                INSERT INTO event_log (story_id, event_type, from_state, to_state, actor, details_json, created_at)
                VALUES (?, 'INPUT_CHANGED_STALE', ?, ?, 'Controller', ?, ?)
                """,
                (story_id, old_state, new_state, json.dumps({"new_sha": new_sha, "change_type": change_type}), now),
            )
        return self.export_state(story_id)

    def determine_review_mode(
        self,
        story_id: str,
        role: str,
        diff_ratio: float = 0.0,
        touched_outside_scope: bool = False,
        baseline_changed_br: bool = False,
        critical_auth_flow_changed: bool = False,
    ) -> str:
        """§8.3: Controller determines FULL vs DELTA review mode."""
        with self._connect() as conn:
            prev = conn.execute(
                "SELECT review_id FROM reviews WHERE story_id = ? AND role = ? ORDER BY created_at DESC LIMIT 1",
                (story_id, role.upper()),
            ).fetchone()
        if not prev:
            return "FULL"
        if diff_ratio > 0.30 or touched_outside_scope or baseline_changed_br or critical_auth_flow_changed:
            return "FULL"
        return "DELTA"

    def reserve_review_slot(
        self,
        story_id: str,
        role: str,
        candidate_sha: str,
        diff_ratio: float = 0.0,
        touched_outside_scope: bool = False,
        baseline_changed_br: bool = False,
        critical_auth_flow_changed: bool = False,
        slot_cost_usd: float = 0.50,
    ) -> dict:
        """
        §8, §14.2, Appendix E: Reserves a review slot BEFORE running LLM reviewer.
        - Requires G3 == PASS on candidate_sha (§8.4 Rule 1).
        - If review_used >= review_limit or budget exceeded -> transitions story to ESCALATED and raises RuntimeError.
        """
        role_up = role.upper()
        if role_up not in ("BIZ", "SEC"):
            raise ValueError(f"Reviewer role must be BIZ or SEC, got: {role}")

        row = self.get_story_row(story_id)
        gates = json.loads(row["gates_json"])
        if gates.get("G3", {}).get("status") != "PASS":
            raise RuntimeError("§8.4 Rule 1 violation: Cannot run review when Gate G3 is not PASS.")

        if row["budget_spent"] + row["budget_reserved"] + slot_cost_usd > row["budget_limit"]:
            self._escalate_story(story_id, "BUDGET_EXCEEDED", f"Budget limit {row['budget_limit']} USD exceeded.")
            raise RuntimeError(f"Story '{story_id}' ESCALATED: Budget limit exceeded.")

        if row["review_used"] >= row["review_limit"]:
            self._escalate_story(
                story_id,
                "REVIEW_CAP_EXCEEDED",
                f"Review cap reached ({row['review_used']}/{row['review_limit']}) for risk_level={row['risk_level']}.",
            )
            raise RuntimeError(
                f"Story '{story_id}' ESCALATED: Review cap reached ({row['review_used']}/{row['review_limit']})."
            )

        mode = self.determine_review_mode(
            story_id,
            role_up,
            diff_ratio=diff_ratio,
            touched_outside_scope=touched_outside_scope,
            baseline_changed_br=baseline_changed_br,
            critical_auth_flow_changed=critical_auth_flow_changed,
        )

        slot_id = f"SLOT-{story_id}-{role_up}-{uuid.uuid4().hex[:8].upper()}"
        model_id = (
            "claude-3-7-opus-pinned"
            if (row["risk_level"] == "HIGH" and mode == "FULL")
            else "claude-3-7-sonnet-pinned"
        )
        now = utc_now_iso()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO review_slots (slot_id, story_id, role, candidate_sha, mode, model, budget_usd, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'RESERVED', ?)
                """,
                (slot_id, story_id, role_up, candidate_sha, mode, model_id, slot_cost_usd, now),
            )
            conn.execute(
                """
                UPDATE stories
                SET review_used = review_used + 1,
                    review_delta_used = review_delta_used + CASE WHEN ? = 'DELTA' THEN 1 ELSE 0 END,
                    budget_reserved = budget_reserved + ?,
                    revision = revision + 1,
                    updated_at = ?
                WHERE story_id = ?
                """,
                (mode, slot_cost_usd, now, story_id),
            )
        self.export_state(story_id)
        return {
            "slot_id": slot_id,
            "story_id": story_id,
            "role": role_up,
            "sha": candidate_sha,
            "mode": mode,
            "model": model_id,
            "budget_usd": slot_cost_usd,
        }

    def _escalate_story(self, story_id: str, code: str, message: str):
        row = self.get_story_row(story_id)
        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE stories SET state = 'ESCALATED', escalation_reason = ?, revision = revision + 1, updated_at = ? WHERE story_id = ?",
                (f"{code}: {message}", now, story_id),
            )
            conn.execute(
                """
                INSERT INTO event_log (story_id, event_type, from_state, to_state, actor, details_json, created_at)
                VALUES (?, 'STORY_ESCALATED', ?, 'ESCALATED', 'Controller', ?, ?)
                """,
                (story_id, row["state"], json.dumps({"code": code, "message": message}), now),
            )
        self.export_state(story_id)

    def validate_and_record_review(
        self,
        story_id: str,
        role: str,
        candidate_sha: str,
        review_payload: dict,
        delta_changed_files: list[str] | None = None,
        cost_usd: float = 0.45,
    ) -> dict:
        """
        §8.4, §14.2, Appendix B:
        1. Validates JSON structure against Appendix B schema rules.
        2. Checks role, story_id, candidate_sha, baseline_manifest_sha256.
        3. Enforces Rule 2 (§8.4): In DELTA mode, filters out new blocking findings on unchanged code unless severity == CRITICAL with evidence.
        4. Enforces blocking=true ONLY on HIGH or CRITICAL findings; LOW/MEDIUM cannot trigger re-review loop.
        5. Routes blocking findings by category (§7.3).
        """
        role_up = role.upper()
        row = self.get_story_row(story_id)

        required_top = {
            "review_id",
            "role",
            "story_id",
            "candidate_sha",
            "baseline_manifest_sha256",
            "mode",
            "verdict",
            "checked_scope",
            "findings",
        }
        missing = required_top - set(review_payload.keys())
        if missing:
            raise ValueError(f"Review JSON missing required fields: {sorted(missing)}")

        allowed_top = required_top | {"previous_review_id", "closed_findings"}
        extra_top = set(review_payload.keys()) - allowed_top
        if extra_top:
            raise ValueError(f"Review JSON contains additionalProperties not allowed: {sorted(extra_top)}")

        if review_payload["role"] != role_up:
            raise ValueError(f"Role mismatch: expected {role_up}, got {review_payload['role']}")
        if review_payload["story_id"] != story_id:
            raise ValueError(f"Story ID mismatch: expected {story_id}, got {review_payload['story_id']}")
        if review_payload["candidate_sha"] != candidate_sha:
            raise ValueError(f"Candidate SHA mismatch: expected {candidate_sha}, got {review_payload['candidate_sha']}")
        if not re.match(r"^[a-f0-9]{40}([a-f0-9]{24})?$", review_payload["candidate_sha"]):
            raise ValueError("Invalid candidate_sha hex pattern")
        if review_payload["baseline_manifest_sha256"] != row["baseline_manifest_sha256"]:
            raise ValueError(
                f"Baseline manifest SHA-256 mismatch: expected {row['baseline_manifest_sha256']}, got {review_payload['baseline_manifest_sha256']}"
            )
        if review_payload["mode"] not in ("FULL", "DELTA"):
            raise ValueError(f"Invalid review mode: {review_payload['mode']}")
        if review_payload["verdict"] not in ("PASS", "FAIL", "BLOCKED"):
            raise ValueError(f"Invalid verdict: {review_payload['verdict']}")
        if not isinstance(review_payload["checked_scope"], list) or len(review_payload["checked_scope"]) < 1:
            raise ValueError("checked_scope must be a non-empty array")

        if review_payload["mode"] == "DELTA":
            if "previous_review_id" not in review_payload or "closed_findings" not in review_payload:
                raise ValueError("DELTA review must include 'previous_review_id' and 'closed_findings'")

        required_finding_fields = {
            "id",
            "severity",
            "category",
            "blocking",
            "reference",
            "location",
            "message",
            "evidence",
            "resolution_condition",
        }
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        valid_categories = set(ERROR_ROUTING_TABLE.keys())

        kept_findings = []
        dropped_findings = []
        routing_actions = []

        delta_set = set(delta_changed_files or [])

        for f in review_payload["findings"]:
            f_missing = required_finding_fields - set(f.keys())
            if f_missing:
                raise ValueError(f"Finding missing required fields: {sorted(f_missing)}")
            f_extra = set(f.keys()) - required_finding_fields
            if f_extra:
                raise ValueError(f"Finding has disallowed extra fields: {sorted(f_extra)}")
            if f["severity"] not in valid_severities:
                raise ValueError(f"Invalid finding severity: {f['severity']}")
            if f["category"] not in valid_categories:
                raise ValueError(f"Invalid finding category: {f['category']}")
            if f["blocking"] and f["severity"] in ("LOW", "MEDIUM"):
                raise ValueError("Appendix B & §8.4 Rule 3 violation: LOW/MEDIUM findings cannot have blocking=true.")

            # §8.4 Rule 2: In DELTA mode, reject new blocking findings outside delta_changed_files unless CRITICAL with evidence
            loc_file = f["location"].split(":")[0]
            if (
                review_payload["mode"] == "DELTA"
                and f["blocking"]
                and delta_set
                and loc_file not in delta_set
                and f["severity"] != "CRITICAL"
            ):
                dropped_findings.append(f["id"])
                continue

            kept_findings.append(f)
            if f["blocking"]:
                route = ERROR_ROUTING_TABLE[f["category"]]
                routing_actions.append(
                    {
                        "finding_id": f["id"],
                        "category": f["category"],
                        "target": route["target"],
                        "action": route["action"],
                    }
                )

        blocking_count = sum(1 for f in kept_findings if f["blocking"])
        effective_verdict = "FAIL" if blocking_count > 0 else review_payload["verdict"]
        if effective_verdict == "FAIL" and blocking_count == 0 and dropped_findings:
            effective_verdict = "PASS"

        now = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reviews (
                    review_id, story_id, role, candidate_sha, baseline_manifest_sha256,
                    mode, verdict, checked_scope_json, findings_json, closed_findings_json,
                    cost_usd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_payload["review_id"],
                    story_id,
                    role_up,
                    candidate_sha,
                    review_payload["baseline_manifest_sha256"],
                    review_payload["mode"],
                    effective_verdict,
                    json.dumps(review_payload["checked_scope"]),
                    json.dumps(kept_findings),
                    json.dumps(review_payload.get("closed_findings", [])),
                    cost_usd,
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE stories
                SET last_reviewed_sha = ?,
                    budget_spent = budget_spent + ?,
                    budget_reserved = MAX(0.0, budget_reserved - 0.50),
                    revision = revision + 1,
                    updated_at = ?
                WHERE story_id = ?
                """,
                (candidate_sha, cost_usd, now, story_id),
            )

        self._try_advance_g4(story_id, candidate_sha)
        self.export_state(story_id)
        return {
            "review_id": review_payload["review_id"],
            "effective_verdict": effective_verdict,
            "kept_findings_count": len(kept_findings),
            "dropped_findings_rule2": dropped_findings,
            "routing_actions": routing_actions,
        }

    def sign_high_risk_g4(self, story_id: str, signer_role: str, signer_name: str, candidate_sha: str) -> dict:
        """§1.3, §6: High-risk stories require both PO and TechLead sign-off at G4."""
        if signer_role not in ("PO", "TechLead"):
            raise ValueError("G4 signer_role must be 'PO' or 'TechLead'")
        row = self.get_story_row(story_id)
        if row["candidate_sha"] != candidate_sha:
            raise ValueError("Cannot sign G4 for mismatched candidate_sha")

        signoffs = json.loads(row["g4_signoffs_json"] or "{}")
        signoffs[signer_role] = {
            "signer": signer_name,
            "candidate_sha": candidate_sha,
            "signed_at": utc_now_iso(),
        }
        with self._connect() as conn:
            conn.execute(
                "UPDATE stories SET g4_signoffs_json = ?, revision = revision + 1, updated_at = ? WHERE story_id = ?",
                (json.dumps(signoffs), utc_now_iso(), story_id),
            )
        self._try_advance_g4(story_id, candidate_sha)
        return self.export_state(story_id)

    def _try_advance_g4(self, story_id: str, candidate_sha: str) -> bool:
        """Checks if both BIZ and SEC reviews passed for candidate_sha (plus PO+TechLead signoffs if HIGH risk)."""
        row = self.get_story_row(story_id)
        with self._connect() as conn:
            biz = conn.execute(
                "SELECT * FROM reviews WHERE story_id = ? AND role = 'BIZ' AND candidate_sha = ? ORDER BY created_at DESC LIMIT 1",
                (story_id, candidate_sha),
            ).fetchone()
            sec = conn.execute(
                "SELECT * FROM reviews WHERE story_id = ? AND role = 'SEC' AND candidate_sha = ? ORDER BY created_at DESC LIMIT 1",
                (story_id, candidate_sha),
            ).fetchone()

        if not biz or not sec:
            return False
        if biz["verdict"] != "PASS" or sec["verdict"] != "PASS":
            return False

        signoffs = json.loads(row["g4_signoffs_json"] or "{}")
        if row["risk_level"] == "HIGH":
            if "PO" not in signoffs or "TechLead" not in signoffs:
                return False

        gates = json.loads(row["gates_json"])
        gates["G4"] = {
            "status": "PASS",
            "evidence_id": f"EV-G4-{biz['review_id']}-{sec['review_id']}",
            "candidate_sha": candidate_sha,
        }
        with self._connect() as conn:
            conn.execute(
                "UPDATE stories SET state = 'QUALITY_PASSED', gates_json = ?, revision = revision + 1, updated_at = ? WHERE story_id = ?",
                (json.dumps(gates), utc_now_iso(), story_id),
            )
        return True

    def verify_review_evidence_on_main(self, story_id: str, commit_sha: str, roles: list[str]) -> dict:
        """
        §8.4 Rule 4, §14.2 (`verify-review-evidence`):
        On main branch after merge: verifies valid BIZ/SEC review evidence exists for commit_sha and current baseline WITHOUT calling LLM.
        """
        row = self.get_story_row(story_id)
        if row["candidate_sha"] != commit_sha:
            raise RuntimeError(f"Main branch SHA ({commit_sha}) does not match reviewed candidate SHA ({row['candidate_sha']}).")

        verified = {}
        with self._connect() as conn:
            for r in roles:
                r_up = r.strip().upper()
                rev = conn.execute(
                    """
                    SELECT * FROM reviews
                    WHERE story_id = ? AND role = ? AND candidate_sha = ? AND baseline_manifest_sha256 = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (story_id, r_up, commit_sha, row["baseline_manifest_sha256"]),
                ).fetchone()
                if not rev or rev["verdict"] != "PASS":
                    raise RuntimeError(f"Missing PASS review evidence for role={r_up} on SHA={commit_sha}")
                verified[r_up] = rev["review_id"]

        return {
            "story_id": story_id,
            "commit_sha": commit_sha,
            "baseline_manifest_sha256": row["baseline_manifest_sha256"],
            "llm_called_on_main": False,
            "verified_reviews": verified,
            "status": "PASS",
        }


def main():
    parser = argparse.ArgumentParser(description="AI-Agent V2.1 Workflow Controller CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-story", help="Initialize or reset a story in SQLite store")
    p_init.add_argument("--story", default="US-012")
    p_init.add_argument("--risk", default="HIGH", choices=["NORMAL", "MEDIUM", "HIGH"])
    p_init.add_argument("--sha", default="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2")
    p_init.add_argument("--state", default="BUILD_PASSED")
    p_init.add_argument("--review-used", type=int, default=5)

    p_status = sub.add_parser("status", help="Export and print story state JSON")
    p_status.add_argument("--story", default="US-012")

    p_reserve = sub.add_parser("reserve-review", help="Reserve an LLM review slot (Appendix E)")
    p_reserve.add_argument("--story", required=True)
    p_reserve.add_argument("--role", required=True, choices=["biz", "sec", "BIZ", "SEC"])
    p_reserve.add_argument("--sha", required=True)
    p_reserve.add_argument("--diff-ratio", type=float, default=0.0)

    p_validate = sub.add_parser("validate-review", help="Validate and record a review JSON output")
    p_validate.add_argument("--story", default="US-012")
    p_validate.add_argument("--role", required=True, choices=["biz", "sec", "BIZ", "SEC"])
    p_validate.add_argument("--sha", required=True)
    p_validate.add_argument("--file", required=True)

    p_evidence = sub.add_parser("verify-review-evidence", help="Verify review evidence on main branch without LLM")
    p_evidence.add_argument("--story", default="US-012")
    p_evidence.add_argument("--sha", required=True)
    p_evidence.add_argument("--roles", default="biz,sec")

    p_sign = sub.add_parser("sign-g4", help="Human co-sign Gate G4 for high-risk story")
    p_sign.add_argument("--story", default="US-012")
    p_sign.add_argument("--role", required=True, choices=["PO", "TechLead"])
    p_sign.add_argument("--signer", required=True)
    p_sign.add_argument("--sha", required=True)

    args = parser.parse_args()
    ctrl = WorkflowController()

    try:
        if args.cmd == "init-story":
            state = ctrl.init_story(
                story_id=args.story,
                risk_level=args.risk,
                candidate_sha=args.sha,
                state=args.state,
                review_used=args.review_used,
            )
            print(json.dumps(state, indent=2, ensure_ascii=False))
        elif args.cmd == "status":
            state = ctrl.export_state(args.story)
            print(json.dumps(state, indent=2, ensure_ascii=False))
        elif args.cmd == "reserve-review":
            slot = ctrl.reserve_review_slot(args.story, args.role, args.sha, diff_ratio=args.diff_ratio)
            print(json.dumps(slot, ensure_ascii=False))
        elif args.cmd == "validate-review":
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            res = ctrl.validate_and_record_review(args.story, args.role, args.sha, payload)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.cmd == "verify-review-evidence":
            roles = [r.strip() for r in args.roles.split(",") if r.strip()]
            res = ctrl.verify_review_evidence_on_main(args.story, args.sha, roles)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.cmd == "sign-g4":
            state = ctrl.sign_high_risk_g4(args.story, args.role, args.signer, args.sha)
            print(json.dumps(state, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"[CONTROLLER_ERROR] {exc}", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
