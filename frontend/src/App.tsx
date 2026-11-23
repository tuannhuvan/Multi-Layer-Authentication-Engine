import React, { useState } from 'react';
import {
  GradeAppealItem,
  PRESET_ACCOUNTS,
  ProblemDetail,
  StudentGradeRow,
  UserSession,
  WorkspaceScope,
  WormAuditEntry,
  calculateGradeLocal,
  callMockerApi,
} from './services/api';
import { WorkspaceSwitcher } from './components/workspace-switcher/WorkspaceSwitcher';
import { StepUpS3Modal } from './components/common/StepUpS3Modal';
import { AdminWorkspace } from './workspaces/admin/AdminWorkspace';
import { BoardWorkspace } from './workspaces/board/BoardWorkspace';
import { TeacherWorkspace } from './workspaces/teacher/TeacherWorkspace';
import { StudentWorkspace } from './workspaces/student/StudentWorkspace';

const INITIAL_STUDENTS: StudentGradeRow[] = [
  {
    student_id: '44444444-5555-6666-7777-888888888804',
    student_code: 'HS001',
    full_name: 'Nguyễn Hải An',
    tx1: 8.5,
    tx2: 8.0,
    exempt_tx2: false,
    midterm: 8.5,
    final_exam: 9.0,
    average_score: 8.6,
    academic_rank: 'GIOI',
    conduct_grade: 'TỐT',
    attendance_present: '44/45 tiết',
    status: 'DRAFT',
  },
  {
    student_id: '44444444-5555-6666-7777-888888888805',
    student_code: 'HS002',
    full_name: 'Trần Minh Châu',
    tx1: 7.5,
    tx2: 7.0,
    exempt_tx2: false,
    midterm: 6.5,
    final_exam: 6.5,
    average_score: 6.7,
    academic_rank: 'KHA',
    conduct_grade: 'TỐT',
    attendance_present: '45/45 tiết',
    status: 'LOCKED_S3',
  },
  {
    student_id: '44444444-5555-6666-7777-888888888806',
    student_code: 'HS003',
    full_name: 'Lê Quốc Bảo',
    tx1: 8.0,
    tx2: 0.0,
    exempt_tx2: true,
    midterm: 8.0,
    final_exam: 8.0,
    average_score: 8.0,
    academic_rank: 'GIOI',
    conduct_grade: 'KHÁ',
    attendance_present: '43/45 tiết',
    status: 'DRAFT',
  },
];

const INITIAL_APPEALS: GradeAppealItem[] = [
  {
    appeal_code: 'GA-2026-089',
    grade_sheet_id: 'GS-2026-HK1-12A1-MATH',
    class_id: '12A1',
    student_code: 'HS002',
    student_name: 'Trần Minh Châu',
    score_component: 'FINAL_EXAM',
    old_score: 6.5,
    proposed_new_score: 8.0,
    reason: 'Chấm sót câu 4b hình học không gian (có biên bản chấm phúc khảo đính kèm)',
    evidence_file_uri: 's3://authshield-evidence/appeals/GA-2026-089-exam-paper.pdf',
    maker_id: '8f14e45f-ceea-467a-a830-15b3a7490101',
    maker_username: 'gv_kiem_pho_ht_01',
    maker_s3_sig: 'SIG-MAKER-S2-7721A9',
    checker_id: null,
    checker_s3_sig: null,
    status: 'PENDING_APPROVAL',
    unlock_window_hours: 24,
    unlock_expires_at: null,
    created_at: '2026-11-23T14:20:00+07:00',
  },
];

const INITIAL_WORM_LOGS: WormAuditEntry[] = [
  {
    id: 2,
    actor_user_id: '8f14e45f-ceea-467a-a830-15b3a7490101',
    actor_role: 'TEACHER',
    acr_level: 'S2',
    subsystem_code: 'PH4_EXAM',
    use_case_code: 'UC-TCH-08',
    action_type: 'CREATE_APPEAL_MAKER',
    target_table: 'grade_appeals',
    target_record_id: 'GA-2026-089',
    after_state: { old_score: 6.5, proposed_new_score: 8.0, status: 'PENDING_APPROVAL' },
    prev_hmac_hash: '6f4b98d1a02c781239481029384710293847102938471029384710293847a1b2',
    entry_hmac_hash: '9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d',
    created_at: '2026-11-23T14:20:05Z',
  },
  {
    id: 1,
    actor_user_id: '11111111-2222-3333-4444-555555555501',
    actor_role: 'ADMIN',
    acr_level: 'S3',
    subsystem_code: 'PH1_AUTH',
    use_case_code: 'UC-ADM-08',
    action_type: 'ASSIGN_DUAL_ROLE',
    target_table: 'user_roles',
    target_record_id: 'gv_kiem_pho_ht_01',
    after_state: { roles: ['ROLE_BOARD', 'ROLE_TEACHER'], no_role_duplication: true },
    prev_hmac_hash: '0000000000000000000000000000000000000000000000000000000000000000',
    entry_hmac_hash: '6f4b98d1a02c781239481029384710293847102938471029384710293847a1b2',
    created_at: '2026-11-23T08:00:00Z',
  },
];

export const App: React.FC = () => {
  const [session, setSession] = useState<UserSession>(PRESET_ACCOUNTS.gv_kiem_pho_ht_01);
  const [selectedClassId, setSelectedClassId] = useState<string>('12A1');
  const [students, setStudents] = useState<StudentGradeRow[]>(INITIAL_STUDENTS);
  const [sheetLockedS3, setSheetLockedS3] = useState<boolean>(false);
  const [appeals, setAppeals] = useState<GradeAppealItem[]>(INITIAL_APPEALS);
  const [wormLogs, setWormLogs] = useState<WormAuditEntry[]>(INITIAL_WORM_LOGS);
  const [attemptsUsed, setAttemptsUsed] = useState<number>(1);
  const [tuitionPaid, setTuitionPaid] = useState<boolean>(false);

  const [stepUpModalOpen, setStepUpModalOpen] = useState<boolean>(false);
  const [stepUpContext, setStepUpContext] = useState<string>('GRADE_LOCK_S3');
  const [alertBanner, setAlertBanner] = useState<{
    type: 'success' | 'error';
    title: string;
    detail: string;
    traceId?: string;
    errorCode?: string;
  } | null>(null);

  const pushWormLog = (
    useCaseCode: string,
    subsystemCode: string,
    actionType: string,
    targetTable: string,
    targetId: string,
    afterState: Record<string, unknown>
  ) => {
    setWormLogs((prev) => {
      const prevHash = prev[0]?.entry_hmac_hash || '0'.repeat(64);
      const nextId = (prev[0]?.id || 0) + 1;
      const randomHex = Array.from({ length: 64 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('');
      const entry: WormAuditEntry = {
        id: nextId,
        actor_user_id: session.user_id,
        actor_role: session.active_scope,
        acr_level: session.current_acr,
        subsystem_code: subsystemCode,
        use_case_code: useCaseCode,
        action_type: actionType,
        target_table: targetTable,
        target_record_id: targetId,
        after_state: afterState,
        prev_hmac_hash: prevHash,
        entry_hmac_hash: randomHex,
        created_at: new Date().toISOString(),
      };
      return [entry, ...prev];
    });
  };

  const showProblemAlert = (problem: ProblemDetail) => {
    setAlertBanner({
      type: 'error',
      title: `HTTP ${problem.status} ${problem.title}`,
      detail: problem.detail,
      traceId: problem.traceId,
      errorCode: problem.error_code,
    });
  };

  const handleSelectPresetAccount = (username: string) => {
    const acc = PRESET_ACCOUNTS[username];
    if (!acc) return;
    setSession({ ...acc });
    setSelectedClassId('12A1');
    setAlertBanner({
      type: 'success',
      title: `UC-01 · Đã chuyển phiên SSO sang '${acc.full_name}'`,
      detail: `Roles: [${acc.roles.join(', ')}] · Active Workspace: ${acc.active_scope} · ACR: ${acc.current_acr}`,
    });
  };

  const handleSwitchWorkspace = async (target: WorkspaceScope) => {
    const roleMap: Record<WorkspaceScope, string> = {
      ADMIN: 'ROLE_ADMIN',
      BOARD: 'ROLE_BOARD',
      TEACHER: 'ROLE_TEACHER',
      STUDENT: 'ROLE_STUDENT',
    };
    const reqRole = roleMap[target];
    if (!session.roles.includes(reqRole)) {
      showProblemAlert({
        type: 'https://authshield.edu.vn/errors/workspace_role_missing',
        title: 'Workspace Switch Denied (PEP Guard)',
        status: 403,
        detail: `Tài khoản '${session.username}' chỉ sở hữu [${session.roles.join(', ')}], không có quyền chuyển sang góc '${target}' (${reqRole}).`,
        error_code: 'WORKSPACE_ROLE_MISSING',
        traceId: `tr-${Math.random().toString(16).slice(2, 14)}`,
      });
      return;
    }

    await callMockerApi('/api/auth/switch-context', session, {
      method: 'POST',
      body: JSON.stringify({ username: session.username, target_workspace: target }),
    });

    const oldScope = session.active_scope;
    setSession((prev) => ({
      ...prev,
      active_scope: target,
      access_token: `eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.${prev.username}.${target}.${prev.current_acr}`,
    }));
    pushWormLog('UC-04', 'PH1_AUTH', 'WORKSPACE_SWITCH', 'workspace_switch_logs', session.username, {
      from_workspace: oldScope,
      to_workspace: target,
    });
    setAlertBanner({
      type: 'success',
      title: `UC-04 · Đã chuyển góc làm việc: ${oldScope} → ${target}`,
      detail: `API Gateway đã cấp Context Token mới với active_scope="${target}" (Hình 7 Sequence 5.1).`,
    });
  };

  const handleTriggerLockoutDemo = async () => {
    const res = await callMockerApi('/api/auth/login', session, {
      method: 'POST',
      body: JSON.stringify({ username: session.username, password: 'wrong_lockout' }),
    });
    if (!res.ok && res.problem) {
      pushWormLog('UC-01', 'PH1_AUTH', 'PROGRESSIVE_LOCKOUT_423', 'users', session.username, {
        locked_duration: '15 minutes',
      });
      showProblemAlert(res.problem);
    }
  };

  const handleConfirmStepUp = async (method: 'SOFT_HSM_S3' | 'FIDO2_PKI_S3', pin: string) => {
    await callMockerApi('/api/auth/step-up/s3', session, {
      method: 'POST',
      body: JSON.stringify({
        username: session.username,
        method,
        pin_or_passkey: pin,
        action_context: stepUpContext,
      }),
    });
    const sig = `S3-${method}-${Math.random().toString(16).slice(2, 10).toUpperCase()}`;
    setSession((prev) => ({ ...prev, current_acr: 'S3', s3_signature: sig }));
    setStepUpModalOpen(false);
    pushWormLog('UC-02', 'PH1_AUTH', 'STEP_UP_S3_VERIFIED', 'step_up_challenges', session.username, {
      method,
      action_context: stepUpContext,
      signature: sig,
    });
    setAlertBanner({
      type: 'success',
      title: 'UC-02 · Đã nâng cấp phiên lên ACR=S3 (Soft-HSM / FIDO2)',
      detail: `Chữ ký số S3: ${sig}. Bạn có thể thực hiện khóa sổ điểm, ký học bạ và phê duyệt phúc khảo Checker.`,
    });
  };

  const handleSelectTeacherClass = async (classId: string) => {
    if (!session.assigned_classes.includes(classId)) {
      const res = await callMockerApi(`/api/v1/classes/${classId}/grades`, session, {
        method: 'PUT',
        body: JSON.stringify({
          student_code: 'HS001',
          class_id: classId,
          tx1: 8,
          tx2: 8,
          midterm: 8,
          final_exam: 8,
        }),
      });
      if (!res.ok && res.problem) {
        pushWormLog(
          'ANTI_IDOR_BLOCK',
          'PH3_TEACHING',
          'ACCESS_DENIED_403',
          'exam_grade_sheets',
          classId,
          { attempted_class: classId, assigned_classes: session.assigned_classes }
        );
        showProblemAlert(res.problem);
      }
      return;
    }
    setSelectedClassId(classId);
  };

  const handleUpdateStudentGrade = (
    studentCode: string,
    tx1: number,
    tx2: number,
    exemptTx2: boolean,
    midterm: number,
    finalExam: number
  ) => {
    setStudents((prev) =>
      prev.map((s) => {
        if (s.student_code !== studentCode) return s;
        const calc = calculateGradeLocal(tx1, tx2, exemptTx2, midterm, finalExam);
        return {
          ...s,
          tx1,
          tx2,
          exempt_tx2: exemptTx2,
          midterm,
          final_exam: finalExam,
          average_score: calc.average_score,
          academic_rank: calc.academic_rank,
        };
      })
    );
  };

  const handleLockGradeSheetS3 = () => {
    if (session.current_acr !== 'S3') {
      setStepUpContext('GRADE_LOCK_S3 (UC-TCH-07)');
      setStepUpModalOpen(true);
      showProblemAlert({
        type: 'https://authshield.edu.vn/errors/step_up_s3_required',
        title: 'Step-Up S3 Required (UC-TCH-07)',
        status: 403,
        detail: 'Khóa bảng điểm chính thức yêu cầu chữ ký số ACR=S3 (Soft-HSM / FIDO2). Vui lòng xác thực trên hộp thoại Step-Up.',
        error_code: 'STEP_UP_S3_REQUIRED',
        traceId: `tr-${Math.random().toString(16).slice(2, 14)}`,
      });
      return;
    }
    setSheetLockedS3(true);
    setStudents((prev) => prev.map((s) => ({ ...s, status: 'LOCKED_S3' })));
    pushWormLog('UC-TCH-07', 'PH4_EXAM', 'LOCK_GRADE_SHEET_S3', 'exam_grade_sheets', 'GS-2026-HK1-12A1-MATH', {
      class_id: '12A1',
      signature: session.s3_signature,
    });
    setAlertBanner({
      type: 'success',
      title: 'UC-TCH-07 · Đã ký số S3 khóa cứng bảng điểm Lớp 12A1',
      detail: 'Mọi chỉnh sửa sau thời điểm này bắt buộc phải đi qua quy trình Phúc khảo Maker-Checker 24h (Hình 8).',
    });
  };

  const handleCreateMakerAppeal = (
    studentCode: string,
    oldScore: number,
    newScore: number,
    reason: string
  ) => {
    const stu = students.find((s) => s.student_code === studentCode);
    const code = `GA-2026-${Math.floor(100 + Math.random() * 900)}`;
    const newAppeal: GradeAppealItem = {
      appeal_code: code,
      grade_sheet_id: 'GS-2026-HK1-12A1-MATH',
      class_id: '12A1',
      student_code: studentCode,
      student_name: stu?.full_name || studentCode,
      score_component: 'FINAL_EXAM',
      old_score: oldScore,
      proposed_new_score: newScore,
      reason,
      evidence_file_uri: `s3://authshield-evidence/appeals/${code}.pdf`,
      maker_id: session.user_id,
      maker_username: session.username,
      maker_s3_sig: `SIG-MAKER-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      checker_id: null,
      checker_s3_sig: null,
      status: 'PENDING_APPROVAL',
      unlock_window_hours: 24,
      unlock_expires_at: null,
      created_at: new Date().toISOString(),
    };
    setAppeals((prev) => [newAppeal, ...prev]);
    pushWormLog('UC-TCH-08', 'PH4_EXAM', 'CREATE_APPEAL_MAKER', 'grade_appeals', code, {
      student_code: studentCode,
      proposed_new_score: newScore,
    });
    setAlertBanner({
      type: 'success',
      title: `UC-18 / UC-TCH-08 · Đã tạo đơn đề nghị sửa điểm ${code} (Maker)`,
      detail: 'Chuyển sang Góc Quản Lý (Ban Lãnh đạo - Tài khoản Hiệu Trưởng) để phê duyệt mở khóa 24 giờ.',
    });
  };

  const handleApproveAppealChecker = async (appealCode: string, simulateSelfApprovalSod02: boolean) => {
    if (session.current_acr !== 'S3') {
      setStepUpContext(`APPEAL_APPROVE_S3 (${appealCode})`);
      setStepUpModalOpen(true);
      showProblemAlert({
        type: 'https://authshield.edu.vn/errors/step_up_s3_required',
        title: 'Step-Up S3 Required (UC-BRD-06 Checker)',
        status: 403,
        detail: 'Ban Lãnh đạo (Checker) phê duyệt mở khóa sửa điểm bắt buộc phải ký số mức ACR=S3.',
        error_code: 'STEP_UP_S3_REQUIRED',
        traceId: `tr-${Math.random().toString(16).slice(2, 14)}`,
      });
      return;
    }

    const checkerId = simulateSelfApprovalSod02
      ? '8f14e45f-ceea-467a-a830-15b3a7490101'
      : '22222222-3333-4444-5555-666666666602';

    const res = await callMockerApi('/api/v1/board/appeals/approve', session, {
      method: 'POST',
      body: JSON.stringify({
        appeal_id: appealCode,
        decision: 'APPROVED',
        checker_id: checkerId,
      }),
    });

    if (!res.ok && res.problem) {
      pushWormLog('SOD_02_BLOCK', 'PH4_EXAM', 'ACCESS_DENIED_403', 'grade_appeals', appealCode, {
        reason: 'maker_id == checker_id blocked by SoD-02',
      });
      showProblemAlert(res.problem);
      return;
    }

    const checkerSig = `SIG-CHECKER-S3-${Math.random().toString(16).slice(2, 10).toUpperCase()}`;
    setAppeals((prev) =>
      prev.map((a) =>
        a.appeal_code === appealCode
          ? {
              ...a,
              status: 'APPROVED',
              checker_id: checkerId,
              checker_s3_sig: checkerSig,
              unlock_expires_at: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
            }
          : a
      )
    );
    setSheetLockedS3(false);
    setStudents((prev) =>
      prev.map((s) => (s.student_code === 'HS002' ? { ...s, status: 'UNLOCKED_FOR_EDIT' } : s))
    );
    pushWormLog('UC-BRD-06', 'PH4_EXAM', 'UNLOCK_MAKER_CHECKER_24H', 'grade_appeals', appealCode, {
      checker_sig: checkerSig,
      window_hours: 24,
    });
    setAlertBanner({
      type: 'success',
      title: `UC-11 / UC-BRD-06 · Đã phê duyệt đơn ${appealCode} & Mở khóa sửa điểm trong 24 giờ!`,
      detail: `Đã kiểm chứng SoD-02 (Maker ≠ Checker) và lưu chữ ký kép (Maker Sig + Checker Sig ${checkerSig}) vào WORM Audit.`,
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <WorkspaceSwitcher
        session={session}
        onSwitchWorkspace={handleSwitchWorkspace}
        onSelectPresetAccount={handleSelectPresetAccount}
        onOpenStepUpModal={() => {
          setStepUpContext('MANUAL_STEP_UP_S3');
          setStepUpModalOpen(true);
        }}
        onTriggerLockoutDemo={handleTriggerLockoutDemo}
      />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* RFC 9457 ProblemDetail / Success Alert Notification */}
        {alertBanner && (
          <div
            className={`mb-6 flex items-start justify-between gap-4 rounded-2xl border p-4 shadow-lg ${
              alertBanner.type === 'error'
                ? 'border-rose-500/50 bg-rose-950/40 text-rose-100'
                : 'border-emerald-500/40 bg-emerald-950/35 text-emerald-100'
            }`}
          >
            <div className="space-y-1 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-bold">{alertBanner.title}</span>
                {alertBanner.errorCode && (
                  <span className="rounded bg-rose-500/30 px-2 py-0.5 font-mono text-[11px] font-bold text-rose-200">
                    {alertBanner.errorCode}
                  </span>
                )}
                {alertBanner.traceId && (
                  <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-sky-300">
                    RFC 9457 traceId: {alertBanner.traceId}
                  </span>
                )}
              </div>
              <p className="text-slate-200">{alertBanner.detail}</p>
            </div>
            <button
              onClick={() => setAlertBanner(null)}
              className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              Đóng
            </button>
          </div>
        )}

        {/* Render Active Workspace */}
        {session.active_scope === 'ADMIN' && (
          <AdminWorkspace
            session={session}
            wormLogs={wormLogs}
            onTestSod01Violation={async () => {
              const res = await callMockerApi('/api/v1/classes/12A1/grades', session, {
                method: 'PUT',
                body: JSON.stringify({
                  student_code: 'HS001',
                  class_id: '12A1',
                  tx1: 10,
                  tx2: 10,
                  midterm: 10,
                  final_exam: 10,
                }),
              });
              if (!res.ok && res.problem) {
                pushWormLog('SOD_01_BLOCK', 'PH2_ADMIN', 'ACCESS_DENIED_403', 'exam_grades', 'HS001', {
                  reason: 'Admin isolated from editing grades (SoD-01)',
                });
                showProblemAlert(res.problem);
              }
            }}
            onTestWormTamperViolation={() => {
              showProblemAlert({
                type: 'https://authshield.edu.vn/errors/sod_03_worm_violation',
                title: 'SoD-03 WORM Immutable Audit Violation',
                status: 403,
                detail:
                  'SOD_03_WORM_VIOLATION: Nhật ký kiểm toán WORM là bất biến (READ-ONLY). Quyền UPDATE/DELETE đã bị REVOKE ở tầng CSDL!',
                error_code: 'SOD_03_WORM_IMMUTABLE',
                traceId: `tr-${Math.random().toString(16).slice(2, 14)}`,
              });
            }}
          />
        )}

        {session.active_scope === 'BOARD' && (
          <BoardWorkspace
            session={session}
            appeals={appeals}
            onApproveAppealChecker={handleApproveAppealChecker}
            onSignTranscriptS3={() => {
              if (session.current_acr !== 'S3') {
                setStepUpContext('TRANSCRIPT_SIGN_S3 (UC-BRD-07)');
                setStepUpModalOpen(true);
                return;
              }
              pushWormLog(
                'UC-BRD-07',
                'PH4_EXAM',
                'SIGN_ELECTRONIC_TRANSCRIPT_S3',
                'digital_transcripts_diplomas',
                'HB-2026-12A1',
                { signed_count: 45, moet_sync: 'SYNCED' }
              );
              setAlertBanner({
                type: 'success',
                title: 'UC-12 / UC-BRD-07 · Đã ký số S3 Học bạ điện tử & Đồng bộ CSDL Ngành Bộ GD&ĐT',
                detail: 'Mã băm SHA-256 của 45 tệp PDF Học bạ đã được niêm phong vào kho WORM Audit.',
              });
            }}
          />
        )}

        {session.active_scope === 'TEACHER' && (
          <TeacherWorkspace
            session={session}
            selectedClassId={selectedClassId}
            students={students}
            sheetLockedS3={sheetLockedS3}
            onSelectClass={handleSelectTeacherClass}
            onUpdateStudentGrade={handleUpdateStudentGrade}
            onLockGradeSheetS3={handleLockGradeSheetS3}
            onCreateMakerAppeal={handleCreateMakerAppeal}
          />
        )}

        {session.active_scope === 'STUDENT' && (
          <StudentWorkspace
            session={session}
            attemptsUsed={attemptsUsed}
            maxAttempts={3}
            tuitionPaid={tuitionPaid}
            onSubmitAssignment={() => {
              if (attemptsUsed >= 3) {
                showProblemAlert({
                  type: 'https://authshield.edu.vn/errors/max_attempts_exceeded',
                  title: 'Max Attempts Exceeded (Hình 9 Bước 7)',
                  status: 400,
                  detail: 'Đã hết số lượt nộp bài cho phép (3/3 lượt)! Hệ thống chống ghi đè sau khi đạt trần.',
                  error_code: 'MAX_ATTEMPTS_EXCEEDED',
                  traceId: `tr-${Math.random().toString(16).slice(2, 14)}`,
                });
                return;
              }
              const nextAttempt = attemptsUsed + 1;
              setAttemptsUsed(nextAttempt);
              setAlertBanner({
                type: 'success',
                title: `UC-20 / UC-STU-07 · Nộp bài lần ${nextAttempt}/3 thành công! (Ghi nhận nộp muộn 30 phút, trừ 10% điểm)`,
                detail:
                  'Tệp bài làm đã lưu vào MinIO/S3 kèm mã băm SHA-256. Điểm gốc 9.0 → Điểm sau trừ phạt muộn: 8.1.',
              });
            }}
            onPayTuitionVnpay={() => {
              setTuitionPaid(true);
              pushWormLog(
                'UC-STU-12',
                'PH5_LMS_FIN',
                'TUITION_PAYMENT_VNPAY_HMAC',
                'tuition_payments',
                'INV-2026-HK1-HS001',
                { amount_paid: 1500000, e_receipt: 'EREC-VNPAY-2026-8812' }
              );
              setAlertBanner({
                type: 'success',
                title: 'UC-21 / UC-STU-12..13 · Thanh toán học phí 1,500,000 VNĐ thành công qua VNPAY!',
                detail: 'Đã đối soát chữ ký Webhook HMAC-SHA256 và phát hành Biên lai điện tử EREC-VNPAY-2026-8812.',
              });
            }}
            onTestStudentIdorViolation={async () => {
              const res = await callMockerApi('/api/v1/student/portal?studentCode=HS002', session);
              if (!res.ok && res.problem) {
                pushWormLog(
                  'UC-STU-01',
                  'PH5_LMS_FIN',
                  'ACCESS_DENIED_403',
                  'student_profiles',
                  'HS002',
                  { reason: 'Gateway Anti-IDOR student_id != token.sub' }
                );
                showProblemAlert(res.problem);
              }
            }}
          />
        )}
      </main>

      <StepUpS3Modal
        isOpen={stepUpModalOpen}
        actionContext={stepUpContext}
        onClose={() => setStepUpModalOpen(false)}
        onConfirmStepUp={handleConfirmStepUp}
      />
    </div>
  );
};

export default App;
