/**
 * AuthShield-LMS Contract-First API Service & PEP Interceptor (SAD Phần II Mục 2.2)
 * - Automatically attaches:
 *   1. `Authorization: Bearer <Access_JWT>`
 *   2. `X-Workspace-Context: <ADMIN | BOARD | TEACHER | STUDENT>`
 *   3. `X-Auth-ACR: <S1 | S2 | S3>`
 *   4. `X-Assigned-Classes: <12A1,10A1>`
 * - Connects to Python Contract Mocker (`http://127.0.0.1:18080`) with seamless built-in deterministic fallback
 *   so UI works both with live Mocker Server and standalone preview.
 */

export type WorkspaceScope = 'ADMIN' | 'BOARD' | 'TEACHER' | 'STUDENT';
export type AcrLevel = 'S1' | 'S2' | 'S3';

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  error_code: string;
  traceId: string;
}

export interface UserSession {
  user_id: string;
  username: string;
  full_name: string;
  email: string;
  vneid_identifier: string;
  roles: string[];
  active_scope: WorkspaceScope;
  current_acr: AcrLevel;
  assigned_classes: string[];
  homeroom_class: string | null;
  teacher_type: 'REGULAR' | 'VISITING' | null;
  contract_end_date: string | null;
  can_view_internal_council_docs: boolean;
  access_token: string;
  s3_signature?: string;
}

export interface StudentGradeRow {
  student_id: string;
  student_code: string;
  full_name: string;
  tx1: number;
  tx2: number;
  exempt_tx2: boolean;
  midterm: number;
  final_exam: number;
  average_score: number;
  academic_rank: 'GIOI' | 'KHA' | 'TRUNG_BINH' | 'YEU';
  conduct_grade: string;
  attendance_present: string;
  status: 'DRAFT' | 'LOCKED_S3' | 'UNLOCKED_FOR_EDIT';
}

export interface GradeAppealItem {
  appeal_code: string;
  grade_sheet_id: string;
  class_id: string;
  student_code: string;
  student_name: string;
  score_component: string;
  old_score: number;
  proposed_new_score: number;
  reason: string;
  evidence_file_uri: string;
  maker_id: string;
  maker_username: string;
  maker_s3_sig: string;
  checker_id: string | null;
  checker_s3_sig: string | null;
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED';
  unlock_window_hours: number;
  unlock_expires_at: string | null;
  created_at: string;
}

export interface WormAuditEntry {
  id: number;
  actor_user_id: string;
  actor_role: string;
  acr_level: AcrLevel;
  subsystem_code: string;
  use_case_code: string;
  action_type: string;
  target_table: string;
  target_record_id: string;
  after_state: Record<string, unknown>;
  prev_hmac_hash: string;
  entry_hmac_hash: string;
  created_at: string;
}

const MOCKER_BASE_URL = 'http://127.0.0.1:18080';

export const PRESET_ACCOUNTS: Record<string, UserSession> = {
  gv_kiem_pho_ht_01: {
    user_id: '8f14e45f-ceea-467a-a830-15b3a7490101',
    username: 'gv_kiem_pho_ht_01',
    full_name: 'TS. Nguyễn Văn Minh (Phó HT kiêm GV Toán)',
    email: 'minh.nv@authshield.edu.vn',
    vneid_identifier: 'VNEID-001085019283',
    roles: ['ROLE_BOARD', 'ROLE_TEACHER'],
    active_scope: 'TEACHER',
    current_acr: 'S2',
    assigned_classes: ['12A1', '10A1'],
    homeroom_class: '12A1',
    teacher_type: 'REGULAR',
    contract_end_date: null,
    can_view_internal_council_docs: true,
    access_token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.gv_kiem_pho_ht_01.TEACHER.S2',
  },
  hieu_truong_01: {
    user_id: '22222222-3333-4444-5555-666666666602',
    username: 'hieu_truong_01',
    full_name: 'NGƯT. Trần Quốc Tuấn (Hiệu Trưởng - Checker S3)',
    email: 'hieutruong@authshield.edu.vn',
    vneid_identifier: 'VNEID-001075009988',
    roles: ['ROLE_BOARD'],
    active_scope: 'BOARD',
    current_acr: 'S2',
    assigned_classes: [],
    homeroom_class: null,
    teacher_type: null,
    contract_end_date: null,
    can_view_internal_council_docs: true,
    access_token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.hieu_truong_01.BOARD.S2',
  },
  gv_thinh_giang_01: {
    user_id: '33333333-4444-5555-6666-777777777703',
    username: 'gv_thinh_giang_01',
    full_name: 'ThS. Phạm Thu Hương (GV Thỉnh giảng Tiếng Anh)',
    email: 'huong.pt@visiting.edu.vn',
    vneid_identifier: 'VNEID-001092004455',
    roles: ['ROLE_TEACHER'],
    active_scope: 'TEACHER',
    current_acr: 'S2',
    assigned_classes: ['12A1'],
    homeroom_class: null,
    teacher_type: 'VISITING',
    contract_end_date: '2027-05-31',
    can_view_internal_council_docs: false,
    access_token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.gv_thinh_giang_01.TEACHER.S2',
  },
  admin_root: {
    user_id: '11111111-2222-3333-4444-555555555501',
    username: 'admin_root',
    full_name: 'Kỹ sư Lê Hoàng Nam (Quản trị viên Hệ thống)',
    email: 'admin@authshield.edu.vn',
    vneid_identifier: 'VNEID-001090001122',
    roles: ['ROLE_ADMIN'],
    active_scope: 'ADMIN',
    current_acr: 'S2',
    assigned_classes: [],
    homeroom_class: null,
    teacher_type: null,
    contract_end_date: null,
    can_view_internal_council_docs: true,
    access_token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.admin_root.ADMIN.S2',
  },
  hs_nguyen_an_12a1: {
    user_id: '44444444-5555-6666-7777-888888888804',
    username: 'hs_nguyen_an_12a1',
    full_name: 'Nguyễn Hải An (Học sinh lớp 12A1 - Mã HS001)',
    email: 'an.nh.12a1@student.authshield.edu.vn',
    vneid_identifier: 'VNEID-001208007766',
    roles: ['ROLE_STUDENT'],
    active_scope: 'STUDENT',
    current_acr: 'S1',
    assigned_classes: ['12A1'],
    homeroom_class: '12A1',
    teacher_type: null,
    contract_end_date: null,
    can_view_internal_council_docs: false,
    access_token: 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.hs_nguyen_an_12a1.STUDENT.S1',
  },
};

export function calculateGradeLocal(tx1: number, tx2: number, exemptTx2: boolean, midterm: number, finalExam: number) {
  const total = exemptTx2 ? tx1 + 2 * midterm + 3 * finalExam : tx1 + tx2 + 2 * midterm + 3 * finalExam;
  const denom = exemptTx2 ? 6 : 7;
  const avg = Math.round((total / denom + Number.EPSILON) * 10) / 10;
  const comps = exemptTx2 ? [tx1, midterm, finalExam] : [tx1, tx2, midterm, finalExam];
  const minScore = Math.min(...comps);
  let rank: 'GIOI' | 'KHA' | 'TRUNG_BINH' | 'YEU' = 'YEU';
  if (avg >= 8.0 && minScore >= 6.5) rank = 'GIOI';
  else if (avg >= 6.5 && minScore >= 5.0) rank = 'KHA';
  else if (avg >= 5.0 && minScore >= 3.5) rank = 'TRUNG_BINH';
  return { average_score: avg, academic_rank: rank };
}

export async function callMockerApi<T>(
  path: string,
  session: UserSession,
  options: RequestInit = {}
): Promise<{ ok: boolean; status: number; data?: T; problem?: ProblemDetail; fromLiveMocker: boolean }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
    'X-Workspace-Context': session.active_scope,
    'X-Auth-ACR': session.current_acr,
    'X-Assigned-Classes': session.assigned_classes.join(','),
    ...(session.s3_signature ? { 'X-StepUp-Signature': session.s3_signature } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  try {
    const resp = await fetch(`${MOCKER_BASE_URL}${path}`, {
      ...options,
      headers,
    });
    const json = await resp.json();
    if (!resp.ok) {
      return { ok: false, status: resp.status, problem: json as ProblemDetail, fromLiveMocker: true };
    }
    return { ok: true, status: resp.status, data: json as T, fromLiveMocker: true };
  } catch {
    // Offline deterministic contract mocker fallback if local port 18080 is not running
    return simulateContractFallback<T>(path, session, options);
  }
}

function makeFallbackProblem(status: number, title: string, detail: string, error_code: string): ProblemDetail {
  const rand = Math.random().toString(16).substring(2, 14);
  return {
    type: `https://authshield.edu.vn/errors/${error_code.toLowerCase()}`,
    title,
    status,
    detail,
    error_code,
    traceId: `tr-${rand}`,
  };
}

function simulateContractFallback<T>(
  path: string,
  session: UserSession,
  options: RequestInit
): { ok: boolean; status: number; data?: T; problem?: ProblemDetail; fromLiveMocker: boolean } {
  const body = options.body ? JSON.parse(String(options.body)) : {};

  if (path === '/api/auth/login' && body.password === 'wrong_lockout') {
    return {
      ok: false,
      status: 423,
      problem: makeFallbackProblem(
        423,
        'Account Temporarily Locked (UC-01 Progressive Lockout)',
        `Tài khoản '${body.username}' đã nhập sai mật khẩu quá ngưỡng và bị khóa lũy tiến 15 phút (HTTP 423 Locked).`,
        'ACCOUNT_PROGRESSIVE_LOCKED'
      ),
      fromLiveMocker: false,
    };
  }

  if (path.startsWith('/api/v1/classes/') && path.endsWith('/grades')) {
    const classId = path.split('/')[4];
    if (session.active_scope === 'ADMIN') {
      return {
        ok: false,
        status: 403,
        problem: makeFallbackProblem(
          403,
          'SoD-01 Admin Grade Isolation',
          'SOD_01_VIOLATION: Quản trị viên hệ thống (ADMIN) bị cách ly hoàn toàn khỏi dữ liệu điểm số!',
          'SOD_01_ADMIN_ISOLATION'
        ),
        fromLiveMocker: false,
      };
    }
    if (!session.assigned_classes.includes(classId)) {
      return {
        ok: false,
        status: 403,
        problem: makeFallbackProblem(
          403,
          'Anti-IDOR Data Scope Blocked',
          `Chặn Anti-IDOR (Hình 7 Bước 26): Giáo viên '${session.full_name}' không được phân công giảng dạy lớp '${classId}'!`,
          'UNIT_SCOPE_FORBIDDEN'
        ),
        fromLiveMocker: false,
      };
    }
  }

  if (path === '/api/v1/board/appeals/approve') {
    if (session.current_acr !== 'S3') {
      return {
        ok: false,
        status: 403,
        problem: makeFallbackProblem(
          403,
          'Step-Up S3 Required',
          'Phê duyệt mở khóa sửa điểm (UC-BRD-06) bắt buộc xác thực chữ ký số mức ACR=S3 (Soft-HSM / FIDO2).',
          'STEP_UP_S3_REQUIRED'
        ),
        fromLiveMocker: false,
      };
    }
    if (body.checker_id === '8f14e45f-ceea-467a-a830-15b3a7490101') {
      return {
        ok: false,
        status: 403,
        problem: makeFallbackProblem(
          403,
          'SoD-02 Maker-Checker Violation',
          'Vi phạm nguyên tắc Phân tách nhiệm vụ SoD-02 (CHECK maker_id != checker_id): Người tạo đơn (Maker) không được tự phê duyệt (Checker) đơn của chính mình!',
          'SOD_02_MAKER_EQUALS_CHECKER'
        ),
        fromLiveMocker: false,
      };
    }
  }

  if (path.includes('studentCode=HS002')) {
    return {
      ok: false,
      status: 403,
      problem: makeFallbackProblem(
        403,
        'Student Anti-IDOR Guard',
        "Gateway Anti-IDOR Guard: Học sinh 'HS001' bị chặn truy cập hồ sơ/điểm của học sinh khác ('HS002')!",
        'STUDENT_IDOR_FORBIDDEN'
      ),
      fromLiveMocker: false,
    };
  }

  return { ok: true, status: 200, data: body as T, fromLiveMocker: false };
}
