#!/usr/bin/env python3
"""
Contract-First Mocker & Business Logic Reference Engine (P4 FE/BE & P3 Acceptance)
Implements OpenAPI contract `api/openapi.yaml` (API-002) and Business Rule `BR-031` (SPEC-003).
Provides:
1. Pure domain functions (`calculate_grade`, `verify_unit_scope_and_acr`, `sign_approval_s3`)
2. Contract validator (`--validate`)
3. Local HTTP Mock Server (`--serve --port 18080`) emitting RFC 9457 ProblemDetail on errors.
"""
import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    """BR-031-01, BR-031-02, BR-031-04 implementation."""
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
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_contract_and_golden(spec_path: Path, golden_path: Path) -> int:
    if not spec_path.exists():
        print(f"[ERROR] OpenAPI spec missing: {spec_path}", file=sys.stderr)
        return 1
    spec_text = spec_path.read_text(encoding="utf-8")
    required_markers = [
        "version: \"API-002\"",
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
    def _send_json(self, status: int, body: dict, content_type: str = "application/json"):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw or "{}")

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

        self._send_json(404, make_problem_detail(404, "Not Found", self.path, "NOT_FOUND"), "application/problem+json")

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw or "{}")

        if self.path.startswith("/api/v1/classes/") and self.path.endswith("/grades"):
            parts = self.path.strip("/").split("/")
            class_id = parts[-2]
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
    parser = argparse.ArgumentParser(description="AuthShield-LMS OpenAPI Contract Mocker V2.1")
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
        server = HTTPServer(("127.0.0.1", args.port), ContractMockHandler)
        print(f"Contract Mocker listening on http://127.0.0.1:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
