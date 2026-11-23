#!/usr/bin/env python3
"""
AuthShield-LMS Contract-First Mocker & Full 6-Subsystem Reference Engine (V2.1)
Implements OpenAPI contract `api/openapi.yaml` (API-002), Business Rule `BR-031` (SPEC-003),
and all 6 Subsystems (PH1..PH6) from the SRS/SAD/DBDD:
- PH1: SSO Login, Progressive Lockout (423 Locked), Workspace Switcher (`BOARD <-> TEACHER`), Step-Up S1/S2/S3 (Soft-HSM / FIDO2)
- PH2: Admin Portal (Academic Year, Grading Policy, User Role Assignment without Role Duplication, SoD-01 Admin blocked from editing grades)
- PH3: Teaching Data Scope (Subject Teacher `12A1` vs `12A2` Anti-IDOR, Visiting Teacher contract expiry & hidden council docs, Homeroom Teacher)
- PH4: Exam Grade Sheets, S3 Digital Signature Lock, Maker-Checker Appeals (`GA-2026-089`, SoD-02 `maker_id != checker_id`, 24h unlock window), Electronic Transcripts
- PH5: Student LMS Assignment Submissions (`max_attempts`, late submission penalty `-10%`, SHA-256 hash) & Tuition Payment (VNPAY/MoMo HMAC-SHA256 + e-Receipt)
- PH6: Executive Dashboard, MOET Sync Reports & Immutable Chained HMAC-SHA256 WORM Audit Logs (SoD-03 Read-Only)
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse
import uuid

REPO_ROOT = Path(__file__).resolve().parents[2]
WORM_HMAC_SECRET = b"AuthShield-LMS-TCVN-11930-Level3-WORM-Secret-Key"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def round_half_up_1dp(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def classify_rank(avg_score: float, component_scores: list[float]) -> str:
    min_score = min(component_scores) if component_scores else 0.0
    if avg_score >= 8.0 and min_score >= 6.5:
        return "GIOI"
    if avg_score >= 6.5 and min_score >= 5.0:
        return "KHA"
    if avg_score >= 5.0 and min_score >= 3.5:
        return "TRUNG_BINH"
    return "YEU"


def calculate_grade(payload: dict) -> dict:
    """BR-031-01, BR-031-02, BR-031-04 deterministic grade calculation."""
    tx1 = Decimal(str(payload["tx1"]))
    tx2 = Decimal(str(payload.get("tx2", 0.0)))
    exempt_tx2 = bool(payload.get("exempt_tx2", False))
    midterm = Decimal(str(payload["midterm"]))
    final_exam = Decimal(str(payload["final_exam"]))

    if exempt_tx2:
        total = tx1 + (Decimal("2") * midterm) + (Decimal("3") * final_exam)
        denominator = Decimal("6")
        components = [float(tx1), float(midterm), float(final_exam)]
    else:
        total = tx1 + tx2 + (Decimal("2") * midterm) + (Decimal("3") * final_exam)
        denominator = Decimal("7")
        components = [float(tx1), float(tx2), float(midterm), float(final_exam)]

    avg = round_half_up_1dp(total / denominator)
    rank = classify_rank(avg, components)
    return {
        "student_code": payload["student_code"],
        "class_id": payload["class_id"],
        "average_score": avg,
        "academic_rank": rank,
        "formula_version": "BR-031-SPEC-003",
    }


def make_problem_detail(status: int, title: str, detail: str, error_code: str) -> dict:
    return {
        "type": f"https://authshield.edu.vn/errors/{error_code.lower()}",
        "title": title,
        "status": status,
        "detail": detail,
        "error_code": error_code,
        "traceId": f"tr-{uuid.uuid4().hex[:12]}",
    }


def verify_unit_scope_and_acr(target_class: str, assigned_classes_header: str, acr_header: str) -> tuple[bool, dict | None]:
    """BR-031-03: Anti-IDOR unit scope check and ACR >= S2 check."""
    assigned = [c.strip() for c in (assigned_classes_header or "").split(",") if c.strip()]
    if acr_header not in ("S2", "S3"):
        return False, make_problem_detail(
            403,
            "Forbidden",
            f"Updating grades requires ACR >= S2 (current: {acr_header}).",
            "STEP_UP_S2_REQUIRED",
        )
    if target_class not in assigned:
        return False, make_problem_detail(
            403,
            "Forbidden",
            f"Anti-IDOR violation: Teacher is not assigned to unit/class '{target_class}'.",
            "UNIT_SCOPE_FORBIDDEN",
        )
    return True, None


def sign_approval_s3(approval_id: str, acr_header: str) -> tuple[int, dict]:
    """BR-031-03: Maker-Checker approval requires ACR == S3 digital signature."""
    if acr_header != "S3":
        return 403, make_problem_detail(
            403,
            "Forbidden",
            f"Maker-Checker approval requires digital signature ACR=S3 (current: {acr_header}).",
            "STEP_UP_S3_REQUIRED",
        )
    return 200, {
        "approval_id": approval_id,
        "status": "APPROVED",
        "acr_verified": "S3",
        "signed_at": utc_now(),
    }


# ==============================================================================
# IN-MEMORY STATE STORE FOR MOCK SERVER (32-TABLE EQUIVALENT DATASET)
# ==============================================================================
class MockDatabase:
    def __init__(self):
        self.worm_logs: list[dict] = []
        self.users = {
            "gv_kiem_pho_ht_01": {
                "user_id": "8f14e45f-ceea-467a-a830-15b3a7490101",
                "username": "gv_kiem_pho_ht_01",
                "full_name": "TS. Nguyễn Văn Minh (Phó HT kiêm GV Toán)",
                "email": "minh.nv@authshield.edu.vn",
                "vneid_identifier": "VNEID-001085019283",
                "roles": ["ROLE_BOARD", "ROLE_TEACHER"],
                "active_scope": "TEACHER",
                "current_acr": "S2",
                "assigned_classes": ["12A1", "10A1"],
                "homeroom_class": "12A1",
                "teacher_type": "REGULAR",
                "contract_end_date": None,
                "can_view_internal_council_docs": True,
                "failed_login_count": 0,
                "account_status": "ACTIVE",
            },
            "admin_root": {
                "user_id": "11111111-2222-3333-4444-555555555501",
                "username": "admin_root",
                "full_name": "Kỹ sư Lê Hoàng Nam (Quản trị viên Hệ thống)",
                "email": "admin@authshield.edu.vn",
                "vneid_identifier": "VNEID-001090001122",
                "roles": ["ROLE_ADMIN"],
                "active_scope": "ADMIN",
                "current_acr": "S2",
                "assigned_classes": [],
                "homeroom_class": None,
                "teacher_type": None,
                "contract_end_date": None,
                "can_view_internal_council_docs": True,
                "failed_login_count": 0,
                "account_status": "ACTIVE",
            },
            "hieu_truong_01": {
                "user_id": "22222222-3333-4444-5555-666666666602",
                "username": "hieu_truong_01",
                "full_name": "NGƯT. Trần Quốc Tuấn (Hiệu Trưởng - Checker S3)",
                "email": "hieutruong@authshield.edu.vn",
                "vneid_identifier": "VNEID-001075009988",
                "roles": ["ROLE_BOARD"],
                "active_scope": "BOARD",
                "current_acr": "S2",
                "assigned_classes": [],
                "homeroom_class": None,
                "teacher_type": None,
                "contract_end_date": None,
                "can_view_internal_council_docs": True,
                "failed_login_count": 0,
                "account_status": "ACTIVE",
            },
            "gv_thinh_giang_01": {
                "user_id": "33333333-4444-5555-6666-777777777703",
                "username": "gv_thinh_giang_01",
                "full_name": "ThS. Phạm Thu Hương (GV Thỉnh giảng Tiếng Anh)",
                "email": "huong.pt@visiting.edu.vn",
                "vneid_identifier": "VNEID-001092004455",
                "roles": ["ROLE_TEACHER"],
                "active_scope": "TEACHER",
                "current_acr": "S2",
                "assigned_classes": ["12A1"],
                "homeroom_class": None,
                "teacher_type": "VISITING",
                "contract_end_date": "2027-05-31",
                "can_view_internal_council_docs": False,
                "failed_login_count": 0,
                "account_status": "ACTIVE",
            },
            "hs_nguyen_an_12a1": {
                "user_id": "44444444-5555-6666-7777-888888888804",
                "username": "hs_nguyen_an_12a1",
                "student_code": "HS001",
                "full_name": "Nguyễn Hải An (Học sinh lớp 12A1)",
                "email": "an.nh.12a1@student.authshield.edu.vn",
                "vneid_identifier": "VNEID-001208007766",
                "roles": ["ROLE_STUDENT"],
                "active_scope": "STUDENT",
                "current_acr": "S1",
                "assigned_classes": ["12A1"],
                "homeroom_class": "12A1",
                "teacher_type": None,
                "contract_end_date": None,
                "can_view_internal_council_docs": False,
                "failed_login_count": 0,
                "account_status": "ACTIVE",
            },
        }

        self.grade_sheets = {
            "12A1": {
                "sheet_id": "GS-2026-HK1-12A1-MATH",
                "class_id": "12A1",
                "subject_code": "MATH",
                "subject_name": "Toán học",
                "assigned_teacher": "gv_kiem_pho_ht_01",
                "sheet_status": "DRAFT",
                "teacher_s3_sig": None,
                "unlock_window_expires_at": None,
                "students": [
                    {
                        "student_id": "44444444-5555-6666-7777-888888888804",
                        "student_code": "HS001",
                        "full_name": "Nguyễn Hải An",
                        "tx1": 8.5,
                        "tx2": 8.0,
                        "exempt_tx2": False,
                        "midterm": 8.5,
                        "final_exam": 9.0,
                        "average_score": 8.6,
                        "academic_rank": "GIOI",
                        "conduct_grade": "TỐT",
                        "attendance_present": "44/45 tiết",
                        "status": "DRAFT",
                    },
                    {
                        "student_id": "44444444-5555-6666-7777-888888888805",
                        "student_code": "HS002",
                        "full_name": "Trần Minh Châu",
                        "tx1": 7.5,
                        "tx2": 7.0,
                        "exempt_tx2": False,
                        "midterm": 6.5,
                        "final_exam": 6.5,
                        "average_score": 6.7,
                        "academic_rank": "KHA",
                        "conduct_grade": "TỐT",
                        "attendance_present": "45/45 tiết",
                        "status": "LOCKED_S3",
                    },
                    {
                        "student_id": "44444444-5555-6666-7777-888888888806",
                        "student_code": "HS003",
                        "full_name": "Lê Quốc Bảo",
                        "tx1": 8.0,
                        "tx2": 0.0,
                        "exempt_tx2": True,
                        "midterm": 8.0,
                        "final_exam": 8.0,
                        "average_score": 8.0,
                        "academic_rank": "GIOI",
                        "conduct_grade": "KHÁ",
                        "attendance_present": "43/45 tiết",
                        "status": "DRAFT",
                    },
                ],
            },
            "12A2": {
                "sheet_id": "GS-2026-HK1-12A2-MATH",
                "class_id": "12A2",
                "subject_code": "MATH",
                "subject_name": "Toán học",
                "assigned_teacher": "gv_toan_12a2",
                "sheet_status": "LOCKED_S3",
                "teacher_s3_sig": "SIG-S3-HSM-998811",
                "unlock_window_expires_at": None,
                "students": [],
            },
        }

        self.grade_appeals = [
            {
                "appeal_code": "GA-2026-089",
                "grade_sheet_id": "GS-2026-HK1-12A1-MATH",
                "class_id": "12A1",
                "student_code": "HS002",
                "student_name": "Trần Minh Châu",
                "score_component": "FINAL_EXAM",
                "old_score": 6.5,
                "proposed_new_score": 8.0,
                "reason": "Chấm sót câu 4b hình học không gian (có biên bản chấm phúc khảo đính kèm)",
                "evidence_file_uri": "s3://authshield-evidence/appeals/GA-2026-089-exam-paper.pdf",
                "maker_id": "8f14e45f-ceea-467a-a830-15b3a7490101",
                "maker_username": "gv_kiem_pho_ht_01",
                "maker_s3_sig": "SIG-MAKER-S2-7721a9",
                "checker_id": None,
                "checker_s3_sig": None,
                "status": "PENDING_APPROVAL",
                "unlock_window_hours": 24,
                "unlock_expires_at": None,
                "created_at": "2026-11-23T14:20:00+07:00",
            }
        ]

        self.assignments = [
            {
                "assignment_id": "ASN-12A1-MATH-45",
                "class_id": "12A1",
                "subject_name": "Toán học",
                "title": "Bài tập Chuyên đề Tích phân & Ứng dụng hình học",
                "deadline": "2026-11-23T23:59:59+07:00",
                "max_attempts": 3,
                "current_attempts": 1,
                "penalty_rate": 10.0,
                "last_submission": {
                    "attempt_number": 1,
                    "file_name": "NguyenHaiAn_12A1_TichPhan_v1.pdf",
                    "file_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                    "submitted_at": "2026-11-24T00:30:00+07:00",
                    "is_late": True,
                    "late_minutes": 30,
                    "penalty_percent": 10.0,
                    "raw_score": 9.0,
                    "final_score": 8.1,
                },
            }
        ]

        self.tuition_invoices = [
            {
                "invoice_code": "INV-2026-HK1-HS001",
                "student_code": "HS001",
                "student_name": "Nguyễn Hải An",
                "student_user_id": "44444444-5555-6666-7777-888888888804",
                "semester": "Học kỳ I (2026 - 2027)",
                "total_amount": 4500000,
                "paid_amount": 3000000,
                "remaining_debt": 1500000,
                "due_date": "2026-12-05",
                "status": "PARTIALLY_PAID",
                "e_receipt_number": "EREC-VNPAY-2026-8812",
            }
        ]

        self.learning_materials = [
            {
                "id": "MAT-01",
                "title": "Đề cương ôn tập Học kỳ I môn Toán 12",
                "subject": "Toán học",
                "visibility_scope": "CLASS_STUDENTS",
                "file_sha256": "a4b9c2d1e5f809123456789abcdef0123456789abcdef0123456789abcdef012",
            },
            {
                "id": "MAT-02",
                "title": "[MẬT] Biên bản Họp Hội đồng Sư phạm & Quy hoạch Đề thi",
                "subject": "Hội đồng trường",
                "visibility_scope": "INTERNAL_COUNCIL_ONLY",
                "file_sha256": "f9e8d7c6b5a409123456789abcdef0123456789abcdef0123456789abcdef999",
            },
        ]

        # Seed initial WORM Chained HMAC Audit Logs
        self.append_worm_log(
            actor_user_id="11111111-2222-3333-4444-555555555501",
            actor_role="ADMIN",
            acr_level="S3",
            subsystem_code="PH1_AUTH",
            use_case_code="UC-ADM-08",
            action_type="ASSIGN_DUAL_ROLE",
            target_table="user_roles",
            target_record_id="gv_kiem_pho_ht_01",
            after_state={"roles": ["ROLE_BOARD", "ROLE_TEACHER"], "no_role_duplication": True},
        )
        self.append_worm_log(
            actor_user_id="8f14e45f-ceea-467a-a830-15b3a7490101",
            actor_role="TEACHER",
            acr_level="S2",
            subsystem_code="PH4_EXAM",
            use_case_code="UC-TCH-08",
            action_type="CREATE_APPEAL_MAKER",
            target_table="grade_appeals",
            target_record_id="GA-2026-089",
            after_state={"old_score": 6.5, "proposed_new_score": 8.0, "status": "PENDING_APPROVAL"},
        )

    def append_worm_log(
        self,
        actor_user_id: str,
        actor_role: str,
        acr_level: str,
        subsystem_code: str,
        use_case_code: str,
        action_type: str,
        target_table: str,
        target_record_id: str,
        after_state: dict,
    ) -> dict:
        """SoD-03: Appends an immutable HMAC-SHA256 chained audit log record."""
        next_id = len(self.worm_logs) + 1
        prev_hash = self.worm_logs[-1]["entry_hmac_hash"] if self.worm_logs else ("0" * 64)
        after_json = json.dumps(after_state, sort_keys=True, ensure_ascii=False)
        msg = f"{next_id}||{actor_user_id}||{use_case_code}||{after_json}||{prev_hash}".encode("utf-8")
        entry_hash = hmac.new(WORM_HMAC_SECRET, msg, hashlib.sha256).hexdigest()
        record = {
            "id": next_id,
            "actor_user_id": actor_user_id,
            "actor_role": actor_role,
            "acr_level": acr_level,
            "subsystem_code": subsystem_code,
            "use_case_code": use_case_code,
            "action_type": action_type,
            "target_table": target_table,
            "target_record_id": target_record_id,
            "after_state": after_state,
            "prev_hmac_hash": prev_hash,
            "entry_hmac_hash": entry_hash,
            "created_at": utc_now(),
        }
        self.worm_logs.append(record)
        return record


MOCK_DB = MockDatabase()


def validate_contract_and_golden(spec_path: Path, golden_path: Path) -> int:
    if not spec_path.exists():
        print(f"[ERROR] OpenAPI spec missing: {spec_path}", file=sys.stderr)
        return 1
    spec_text = spec_path.read_text(encoding="utf-8")
    required_markers = [
        "version: \"API-002\"",
        "/api/auth/login",
        "/api/auth/switch-context",
        "/api/auth/step-up/s3",
        "/api/v1/grades/calculate",
        "/api/v1/classes/{classId}/grades",
        "/api/v1/grades/approvals/{approvalId}/sign",
        "ProblemDetail",
        "traceId",
    ]
    for marker in required_markers:
        if marker not in spec_text:
            print(f"[ERROR] Contract missing required marker: {marker}", file=sys.stderr)
            return 1

    if not golden_path.exists():
        print(f"[ERROR] Golden dataset missing: {golden_path}", file=sys.stderr)
        return 1

    with golden_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print("[ERROR] Golden dataset is empty!", file=sys.stderr)
            return 1
        for row in rows:
            res = calculate_grade(
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
            exp_avg = float(row["expected_avg"])
            exp_rank = row["expected_rank"]
            if res["average_score"] != exp_avg or res["academic_rank"] != exp_rank:
                print(
                    f"[ERROR] Golden mismatch on {row['case_id']}: got {res}, expected avg={exp_avg}, rank={exp_rank}",
                    file=sys.stderr,
                )
                return 1
    print(f"[OK] Contract '{spec_path.name}' and {len(rows)} golden cases verified successfully.")
    return 0


class ContractMockHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Workspace-Context, X-Auth-ACR, X-Assigned-Classes, X-StepUp-Signature, X-User-Id",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")

    def _send_json(self, status: int, body: dict | list, content_type: str = "application/json"):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/v1/admin/overview":
            self._send_json(
                200,
                {
                    "academic_year": {
                        "code": "2026-2027",
                        "name": "Năm học 2026 - 2027",
                        "semester": "Học kỳ I",
                        "grade_entry_deadline": "2026-12-20T23:59:59+07:00",
                        "status": "ACTIVE",
                    },
                    "grading_policy": {
                        "oral_weight": 1,
                        "quiz_15m_weight": 1,
                        "period_45m_weight": 2,
                        "final_exam_weight": 3,
                        "late_submission_default_penalty": 10.0,
                    },
                    "users": list(MOCK_DB.users.values()),
                    "external_integrations": [
                        {"provider_type": "MOET_API", "provider_name": "Trục Liên thông CSDL Ngành Bộ GD&ĐT", "status": "CONNECTED"},
                        {"provider_type": "VNEID_NDXP", "provider_name": "Định danh Điện tử Quốc gia VNeID Mức 2", "status": "CONNECTED"},
                        {"provider_type": "PAYMENT_VNPAY", "provider_name": "Cổng Thanh toán VNPAY / MoMo (HMAC-SHA256)", "status": "CONNECTED"},
                        {"provider_type": "SMS_BRANDNAME", "provider_name": "Cổng SMS Brandname & Zalo ZNS", "status": "CONNECTED"},
                    ],
                    "worm_audit_logs": list(reversed(MOCK_DB.worm_logs)),
                },
            )
            return

        if path == "/api/v1/admin/audit-logs":
            self._send_json(200, {"logs": list(reversed(MOCK_DB.worm_logs)), "sod03_read_only": True})
            return

        if path == "/api/v1/board/statistics":
            scope = self.headers.get("X-Workspace-Context", "BOARD")
            if scope != "BOARD":
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "Workspace Scope Violation",
                        f"API '/api/v1/board/statistics' requires X-Workspace-Context='BOARD' (current: '{scope}'). Switch workspace first!",
                        "WORKSPACE_CONTEXT_MISMATCH",
                    ),
                    "application/problem+json",
                )
                return
            self._send_json(
                200,
                {
                    "total_students": 1240,
                    "attendance_rate_today": 98.4,
                    "locked_grade_sheets": 38,
                    "total_grade_sheets": 42,
                    "tuition_collection_rate": 91.5,
                    "grade_distribution": {
                        "GIOI": 42.5,
                        "KHA": 38.0,
                        "TRUNG_BINH": 16.5,
                        "YEU": 3.0,
                    },
                    "appeals": MOCK_DB.grade_appeals,
                    "moet_sync_status": "SYNCED (1,240 Học bạ điện tử S3)",
                },
            )
            return

        if path == "/api/v1/teacher/classroom":
            username = query.get("username", ["gv_kiem_pho_ht_01"])[0]
            class_id = query.get("classId", ["12A1"])[0]
            user = MOCK_DB.users.get(username, MOCK_DB.users["gv_kiem_pho_ht_01"])

            if class_id not in user["assigned_classes"]:
                MOCK_DB.append_worm_log(
                    actor_user_id=user["user_id"],
                    actor_role="TEACHER",
                    acr_level=user["current_acr"],
                    subsystem_code="PH3_TEACHING",
                    use_case_code="ANTI_IDOR_BLOCK",
                    action_type="ACCESS_DENIED_403",
                    target_table="exam_grade_sheets",
                    target_record_id=class_id,
                    after_state={"blocked_class": class_id, "assigned_classes": user["assigned_classes"]},
                )
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "Anti-IDOR Data Scope Blocked",
                        f"Chặn Anti-IDOR (Hình 7 Bước 26): Giáo viên '{user['full_name']}' không được phân công giảng dạy lớp '{class_id}'!",
                        "UNIT_SCOPE_FORBIDDEN",
                    ),
                    "application/problem+json",
                )
                return

            materials = [
                m
                for m in MOCK_DB.learning_materials
                if user["can_view_internal_council_docs"] or m["visibility_scope"] != "INTERNAL_COUNCIL_ONLY"
            ]
            self._send_json(
                200,
                {
                    "teacher": user,
                    "grade_sheet": MOCK_DB.grade_sheets.get(class_id),
                    "materials": materials,
                    "appeals": MOCK_DB.grade_appeals,
                },
            )
            return

        if path == "/api/v1/student/portal":
            requested_student_code = query.get("studentCode", ["HS001"])[0]
            token_student_code = "HS001"
            if requested_student_code != token_student_code:
                MOCK_DB.append_worm_log(
                    actor_user_id="44444444-5555-6666-7777-888888888804",
                    actor_role="STUDENT",
                    acr_level="S1",
                    subsystem_code="PH5_LMS_FIN",
                    use_case_code="UC-STU-01",
                    action_type="ACCESS_DENIED_403",
                    target_table="student_profiles",
                    target_record_id=requested_student_code,
                    after_state={"reason": "Gateway Anti-IDOR student_id != token.sub"},
                )
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "Student Anti-IDOR Guard",
                        f"Gateway Anti-IDOR Guard: Học sinh '{token_student_code}' bị chặn truy cập hồ sơ/điểm của học sinh khác ('{requested_student_code}')!",
                        "STUDENT_IDOR_FORBIDDEN",
                    ),
                    "application/problem+json",
                )
                return

            self._send_json(
                200,
                {
                    "profile": MOCK_DB.users["hs_nguyen_an_12a1"],
                    "grades": MOCK_DB.grade_sheets["12A1"]["students"][0],
                    "assignments": MOCK_DB.assignments,
                    "invoices": MOCK_DB.tuition_invoices,
                },
            )
            return

        self._send_json(404, make_problem_detail(404, "Not Found", path, "NOT_FOUND"), "application/problem+json")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw or "{}")

        if self.path == "/api/auth/login":
            username = payload.get("username", "gv_kiem_pho_ht_01")
            password = payload.get("password", "")
            user = MOCK_DB.users.get(username)
            if not user:
                self._send_json(401, make_problem_detail(401, "Unauthorized", "Tài khoản không tồn tại", "AUTH_FAILED"), "application/problem+json")
                return

            if password == "wrong_lockout" or user["failed_login_count"] >= 5:
                user["failed_login_count"] += 1
                user["account_status"] = "TEMP_LOCKED"
                MOCK_DB.append_worm_log(
                    actor_user_id=user["user_id"],
                    actor_role=user["active_scope"],
                    acr_level="S1",
                    subsystem_code="PH1_AUTH",
                    use_case_code="UC-01",
                    action_type="PROGRESSIVE_LOCKOUT_423",
                    target_table="users",
                    target_record_id=username,
                    after_state={"failed_login_count": user["failed_login_count"], "locked_duration": "15 minutes"},
                )
                self._send_json(
                    423,
                    make_problem_detail(
                        423,
                        "Account Temporarily Locked (UC-01 Progressive Lockout)",
                        f"Tài khoản '{username}' đã nhập sai mật khẩu quá ngưỡng và bị khóa lũy tiến 15 phút (HTTP 423 Locked).",
                        "ACCOUNT_PROGRESSIVE_LOCKED",
                    ),
                    "application/problem+json",
                )
                return

            user["failed_login_count"] = 0
            user["account_status"] = "ACTIVE"
            self._send_json(
                200,
                {
                    **user,
                    "access_token": f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{username}.{user['active_scope']}.{user['current_acr']}",
                },
            )
            return

        if self.path == "/api/auth/switch-context":
            username = payload.get("username", "gv_kiem_pho_ht_01")
            target_ws = payload.get("target_workspace", "BOARD")
            user = MOCK_DB.users.get(username, MOCK_DB.users["gv_kiem_pho_ht_01"])
            role_map = {
                "ADMIN": "ROLE_ADMIN",
                "BOARD": "ROLE_BOARD",
                "TEACHER": "ROLE_TEACHER",
                "STUDENT": "ROLE_STUDENT",
            }
            req_role = role_map.get(target_ws)
            if req_role not in user["roles"]:
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "Workspace Switch Denied",
                        f"Tài khoản '{username}' không sở hữu quyền '{req_role}' để chuyển sang góc '{target_ws}'.",
                        "WORKSPACE_ROLE_MISSING",
                    ),
                    "application/problem+json",
                )
                return

            old_ws = user["active_scope"]
            user["active_scope"] = target_ws
            MOCK_DB.append_worm_log(
                actor_user_id=user["user_id"],
                actor_role=target_ws,
                acr_level=user["current_acr"],
                subsystem_code="PH1_AUTH",
                use_case_code="UC-04",
                action_type="WORKSPACE_SWITCH",
                target_table="workspace_switch_logs",
                target_record_id=username,
                after_state={"from_workspace": old_ws, "to_workspace": target_ws},
            )
            self._send_json(
                200,
                {
                    **user,
                    "access_token": f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{username}.{target_ws}.{user['current_acr']}",
                },
            )
            return

        if self.path == "/api/auth/step-up/s3":
            username = payload.get("username", "gv_kiem_pho_ht_01")
            method = payload.get("method", "SOFT_HSM_S3")
            action_ctx = payload.get("action_context", "GRADE_LOCK_S3")
            user = MOCK_DB.users.get(username, MOCK_DB.users["gv_kiem_pho_ht_01"])
            user["current_acr"] = "S3"
            sig = f"S3-{method}-{hashlib.sha256(f'{username}:{action_ctx}:{utc_now()}'.encode()).hexdigest()[:16].upper()}"
            MOCK_DB.append_worm_log(
                actor_user_id=user["user_id"],
                actor_role=user["active_scope"],
                acr_level="S3",
                subsystem_code="PH1_AUTH",
                use_case_code="UC-02",
                action_type="STEP_UP_S3_VERIFIED",
                target_table="step_up_challenges",
                target_record_id=username,
                after_state={"method": method, "action_context": action_ctx, "signature": sig},
            )
            self._send_json(
                200,
                {
                    "current_acr": "S3",
                    "s3_signature": sig,
                    "step_up_s3_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                },
            )
            return

        if self.path == "/api/v1/grades/calculate":
            result = calculate_grade(payload)
            self._send_json(200, result)
            return

        if self.path.startswith("/api/v1/grades/approvals/") and self.path.endswith("/sign"):
            parts = self.path.strip("/").split("/")
            approval_id = parts[-2]
            acr = self.headers.get("X-Auth-ACR", "S1")
            status, body = sign_approval_s3(approval_id, acr)
            ctype = "application/json" if status == 200 else "application/problem+json"
            self._send_json(status, body, ctype)
            return

        if self.path == "/api/v1/board/appeals/approve":
            acr = self.headers.get("X-Auth-ACR", "S2")
            checker_id = payload.get("checker_id", "22222222-3333-4444-5555-666666666602")
            appeal_id = payload.get("appeal_id", "GA-2026-089")
            if acr != "S3":
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "Step-Up S3 Required",
                        "Phê duyệt mở khóa sửa điểm (UC-BRD-06) bắt buộc xác thực chữ ký số mức ACR=S3 (Soft-HSM / FIDO2).",
                        "STEP_UP_S3_REQUIRED",
                    ),
                    "application/problem+json",
                )
                return

            appeal = next((a for a in MOCK_DB.grade_appeals if a["appeal_code"] == appeal_id), MOCK_DB.grade_appeals[0])
            if appeal["maker_id"] == checker_id:
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "SoD-02 Maker-Checker Violation",
                        "Vi phạm nguyên tắc Phân tách nhiệm vụ SoD-02 (CHECK maker_id != checker_id): Người tạo đơn (Maker) không được tự phê duyệt (Checker) đơn của chính mình!",
                        "SOD_02_MAKER_EQUALS_CHECKER",
                    ),
                    "application/problem+json",
                )
                return

            appeal["status"] = "APPROVED"
            appeal["checker_id"] = checker_id
            appeal["checker_s3_sig"] = f"SIG-CHECKER-S3-{uuid.uuid4().hex[:10].upper()}"
            appeal["unlock_expires_at"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

            for stu in MOCK_DB.grade_sheets["12A1"]["students"]:
                if stu["student_code"] == appeal["student_code"]:
                    stu["status"] = "UNLOCKED_FOR_EDIT"

            worm_rec = MOCK_DB.append_worm_log(
                actor_user_id=checker_id,
                actor_role="BOARD",
                acr_level="S3",
                subsystem_code="PH4_EXAM",
                use_case_code="UC-BRD-06",
                action_type="UNLOCK_MAKER_CHECKER_24H",
                target_table="grade_appeals",
                target_record_id=appeal_id,
                after_state={
                    "maker_sig": appeal["maker_s3_sig"],
                    "checker_sig": appeal["checker_s3_sig"],
                    "window_hours": 24,
                },
            )
            self._send_json(200, {"appeal": appeal, "worm_audit_entry": worm_rec})
            return

        if self.path.startswith("/api/v1/student/assignments/") and self.path.endswith("/submit"):
            asn = MOCK_DB.assignments[0]
            if asn["current_attempts"] >= asn["max_attempts"]:
                self._send_json(
                    400,
                    make_problem_detail(
                        400,
                        "Max Attempts Exceeded",
                        f"Đã hết số lượt nộp bài cho phép ({asn['current_attempts']}/{asn['max_attempts']})! (Hình 9 Bước 7)",
                        "MAX_ATTEMPTS_EXCEEDED",
                    ),
                    "application/problem+json",
                )
                return

            asn["current_attempts"] += 1
            file_name = payload.get("file_name", f"NguyenHaiAn_12A1_TichPhan_v{asn['current_attempts']}.pdf")
            file_hash = hashlib.sha256(f"{file_name}:{utc_now()}".encode("utf-8")).hexdigest()
            sub = {
                "attempt_number": asn["current_attempts"],
                "file_name": file_name,
                "file_hash": file_hash,
                "submitted_at": utc_now(),
                "is_late": True,
                "late_minutes": 30,
                "penalty_percent": 10.0,
                "raw_score": 9.0,
                "final_score": 8.1,
            }
            asn["last_submission"] = sub
            self._send_json(
                200,
                {
                    "message": "Nộp bài thành công! (Ghi nhận nộp muộn 30 phút, trừ 10% điểm theo Hình 9 Bước 12)",
                    "submission": sub,
                    "current_attempts": asn["current_attempts"],
                    "max_attempts": asn["max_attempts"],
                },
            )
            return

        self._send_json(404, make_problem_detail(404, "Not Found", self.path, "NOT_FOUND"), "application/problem+json")

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw or "{}")

        if self.path.startswith("/api/v1/classes/") and self.path.endswith("/grades"):
            parts = self.path.strip("/").split("/")
            class_id = parts[-2]
            scope = self.headers.get("X-Workspace-Context", "TEACHER")
            if scope == "ADMIN":
                self._send_json(
                    403,
                    make_problem_detail(
                        403,
                        "SoD-01 Admin Grade Isolation",
                        "SOD_01_VIOLATION: Quản trị viên hệ thống (ADMIN) bị cách ly hoàn toàn khỏi dữ liệu điểm số!",
                        "SOD_01_ADMIN_ISOLATION",
                    ),
                    "application/problem+json",
                )
                return

            acr = self.headers.get("X-Auth-ACR", "S1")
            assigned = self.headers.get("X-Assigned-Classes", "")
            ok, err = verify_unit_scope_and_acr(class_id, assigned, acr)
            if not ok:
                self._send_json(403, err, "application/problem+json")
                return
            payload["class_id"] = class_id
            self._send_json(200, calculate_grade(payload))
            return

        self._send_json(404, make_problem_detail(404, "Not Found", self.path, "NOT_FOUND"), "application/problem+json")


def main():
    parser = argparse.ArgumentParser(description="AuthShield-LMS OpenAPI Contract Mocker V2.1 (6 Subsystems)")
    parser.add_argument("--spec", default="api/openapi.yaml", help="Path to OpenAPI YAML")
    parser.add_argument("--golden", default="docs/spec/golden/grade_calculation_golden.csv", help="Path to Golden CSV")
    parser.add_argument("--validate", action="store_true", help="Validate contract and golden dataset")
    parser.add_argument("--serve", action="store_true", help="Run HTTP mock server")
    parser.add_argument("--port", type=int, default=18080, help="Port for mock server")
    args = parser.parse_args()

    spec_path = (REPO_ROOT / args.spec).resolve()
    golden_path = (REPO_ROOT / args.golden).resolve()

    if args.validate:
        sys.exit(validate_contract_and_golden(spec_path, golden_path))

    if args.serve:
        server = HTTPServer(("0.0.0.0", args.port), ContractMockHandler)
        print(f"AuthShield-LMS Contract Mocker listening on http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
