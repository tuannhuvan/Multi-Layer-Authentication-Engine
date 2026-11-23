import React, { useState } from 'react';
import { StudentGradeRow, UserSession } from '../../services/api';

interface TeacherWorkspaceProps {
  session: UserSession;
  selectedClassId: string;
  students: StudentGradeRow[];
  sheetLockedS3: boolean;
  onSelectClass: (classId: string) => void;
  onUpdateStudentGrade: (
    studentCode: string,
    tx1: number,
    tx2: number,
    exemptTx2: boolean,
    midterm: number,
    finalExam: number
  ) => void;
  onLockGradeSheetS3: () => void;
  onCreateMakerAppeal: (studentCode: string, oldScore: number, newScore: number, reason: string) => void;
}

export const TeacherWorkspace: React.FC<TeacherWorkspaceProps> = ({
  session,
  selectedClassId,
  students,
  sheetLockedS3,
  onSelectClass,
  onUpdateStudentGrade,
  onLockGradeSheetS3,
  onCreateMakerAppeal,
}) => {
  const [appealTarget, setAppealTarget] = useState<string>('HS002');
  const [proposedScore, setProposedScore] = useState<number>(8.0);
  const [appealReason, setAppealReason] = useState<string>(
    'Chấm sót câu 4b hình học không gian (đính kèm bản chụp bài thi gốc)'
  );

  return (
    <div className="space-y-6">
      {/* Teacher Scope Banner */}
      <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-emerald-500/15 via-slate-900 to-slate-900 p-5">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-bold text-emerald-300">
                PH3 & PH4 · Góc Giảng Dạy Giáo Viên (UC-TCH-01..15)
              </span>
              {session.teacher_type === 'VISITING' ? (
                <span className="rounded-full border border-amber-500/40 bg-amber-500/15 px-2.5 py-0.5 text-xs font-bold text-amber-300">
                  GV Thỉnh Giảng · Hạn HĐ: {session.contract_end_date} (Đã ẩn tài liệu Hội đồng UC-TCH-10)
                </span>
              ) : (
                <span className="rounded-full border border-sky-500/40 bg-sky-500/15 px-2.5 py-0.5 text-xs font-bold text-sky-300">
                  GV Cơ Hữu & Chủ Nhiệm Lớp {session.homeroom_class || '12A1'} (UC-TCH-11)
                </span>
              )}
            </div>
            <h2 className="mt-2 text-xl font-bold text-white">
              Sổ Điểm Cá Nhân, Ký Số Khóa Bảng Điểm S3 & Gửi Đơn Sửa Điểm (Maker)
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Chốt chặn <b>Anti-IDOR Data Scope (Hình 7)</b>: Dù có quyền kiêm nhiệm <code className="text-purple-300">ROLE_BOARD</code>, khi ở <code className="text-emerald-300">X-Workspace-Context: TEACHER</code>, chỉ được nhập điểm lớp được phân công (<b>{session.assigned_classes.join(', ')}</b>).
            </p>
          </div>

          {/* Class Selector to test 12A1 (200 OK) vs 12A2 (403 Anti-IDOR) */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onSelectClass('12A1')}
              className={`rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                selectedClassId === '12A1'
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                  : 'border border-slate-700 bg-slate-900 text-slate-300'
              }`}
            >
              📘 Lớp 12A1 (Được phân công · 200 OK)
            </button>
            <button
              onClick={() => onSelectClass('12A2')}
              className="rounded-xl border border-rose-500/50 bg-rose-500/15 px-3.5 py-2 text-xs font-bold text-rose-200 hover:bg-rose-500/25"
              title="Thử truy cập hoặc sửa điểm lớp 12A2 không được phân công -> Chặn 403 Anti-IDOR (Hình 7 Bước 26)"
            >
              🚫 Thử Vào Lớp 12A2 (Test Chặn 403 Anti-IDOR)
            </button>
          </div>
        </div>
      </div>

      {/* Grade Sheet Table (BR-031 HALF_UP & Exempt Weight = 0) */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">
              UC-16 / UC-TCH-02 & 07 · Bảng Điểm Môn Toán Lớp {selectedClassId} (Chuẩn BR-031 HALF_UP)
            </h3>
            <p className="text-xs text-slate-400">
              Hỗ trợ miễn trừ cột điểm (<code className="text-sky-300">exempt_tx2 = true → weight = 0</code> theo AC-012-04). Bảng điểm đã khóa S3 không thể sửa trực tiếp nếu chưa qua Maker-Checker.
            </p>
          </div>
          <button
            onClick={onLockGradeSheetS3}
            className="rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:from-purple-500 hover:to-indigo-500"
          >
            {sheetLockedS3 ? '🔒 Đã Ký Số Khóa Sổ S3' : '🔐 Ký Số S3 Khóa Bảng Điểm (UC-TCH-07)'}
          </button>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-2">Mã HS</th>
                <th className="pb-2">Họ và Tên Học Sinh</th>
                <th className="pb-2">TX1 (HS1)</th>
                <th className="pb-2">TX2 (HS1)</th>
                <th className="pb-2">Miễn TX2</th>
                <th className="pb-2">Giữa Kỳ (HS2)</th>
                <th className="pb-2">Cuối Kỳ (HS3)</th>
                <th className="pb-2">ĐTBm (BR-031)</th>
                <th className="pb-2">Xếp Loại</th>
                <th className="pb-2">Trạng Thái Sổ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {students.map((stu) => {
                const isRowLocked = stu.status === 'LOCKED_S3' || sheetLockedS3;
                return (
                  <tr key={stu.student_code} className="hover:bg-slate-800/30">
                    <td className="py-3 font-mono font-bold text-sky-300">{stu.student_code}</td>
                    <td className="py-3 font-semibold text-white">{stu.full_name}</td>
                    <td className="py-3">
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="10"
                        disabled={isRowLocked}
                        value={stu.tx1}
                        onChange={(e) =>
                          onUpdateStudentGrade(
                            stu.student_code,
                            parseFloat(e.target.value) || 0,
                            stu.tx2,
                            stu.exempt_tx2,
                            stu.midterm,
                            stu.final_exam
                          )
                        }
                        className="w-16 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-center font-mono text-white disabled:opacity-50"
                      />
                    </td>
                    <td className="py-3">
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="10"
                        disabled={isRowLocked || stu.exempt_tx2}
                        value={stu.tx2}
                        onChange={(e) =>
                          onUpdateStudentGrade(
                            stu.student_code,
                            stu.tx1,
                            parseFloat(e.target.value) || 0,
                            stu.exempt_tx2,
                            stu.midterm,
                            stu.final_exam
                          )
                        }
                        className="w-16 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-center font-mono text-white disabled:opacity-50"
                      />
                    </td>
                    <td className="py-3">
                      <input
                        type="checkbox"
                        disabled={isRowLocked}
                        checked={stu.exempt_tx2}
                        onChange={(e) =>
                          onUpdateStudentGrade(
                            stu.student_code,
                            stu.tx1,
                            stu.tx2,
                            e.target.checked,
                            stu.midterm,
                            stu.final_exam
                          )
                        }
                        className="h-4 w-4 rounded accent-emerald-500"
                      />
                    </td>
                    <td className="py-3">
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="10"
                        disabled={isRowLocked}
                        value={stu.midterm}
                        onChange={(e) =>
                          onUpdateStudentGrade(
                            stu.student_code,
                            stu.tx1,
                            stu.tx2,
                            stu.exempt_tx2,
                            parseFloat(e.target.value) || 0,
                            stu.final_exam
                          )
                        }
                        className="w-16 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-center font-mono text-white disabled:opacity-50"
                      />
                    </td>
                    <td className="py-3">
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="10"
                        disabled={isRowLocked}
                        value={stu.final_exam}
                        onChange={(e) =>
                          onUpdateStudentGrade(
                            stu.student_code,
                            stu.tx1,
                            stu.tx2,
                            stu.exempt_tx2,
                            stu.midterm,
                            parseFloat(e.target.value) || 0
                          )
                        }
                        className="w-16 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-center font-mono text-white disabled:opacity-50"
                      />
                    </td>
                    <td className="py-3 font-mono text-sm font-black text-emerald-400">
                      {stu.average_score.toFixed(1)}
                    </td>
                    <td className="py-3">
                      <span
                        className={`rounded-md px-2 py-0.5 font-bold ${
                          stu.academic_rank === 'GIOI'
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : stu.academic_rank === 'KHA'
                            ? 'bg-sky-500/20 text-sky-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}
                      >
                        {stu.academic_rank}
                      </span>
                    </td>
                    <td className="py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          stu.status === 'LOCKED_S3'
                            ? 'bg-rose-500/20 text-rose-300'
                            : stu.status === 'UNLOCKED_FOR_EDIT'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {stu.status === 'LOCKED_S3'
                          ? '🔒 Đã Khóa S3'
                          : stu.status === 'UNLOCKED_FOR_EDIT'
                          ? '🔓 Mở Khóa 24h'
                          : '📝 Bản Nháp (DRAFT)'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Maker Appeal Form & Homeroom Management */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400">
            UC-18 / UC-TCH-08 · Gửi Đơn Đề Nghị Mở Khóa Sửa Điểm (Vai Trò Maker)
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            Khi điểm đã khóa S3 (như HS002 Trần Minh Châu), Giáo viên tạo đơn phúc khảo để Ban Lãnh đạo (Checker) duyệt mở cửa sổ sửa điểm 24 giờ.
          </p>
          <div className="mt-4 space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400">Chọn Học sinh cần sửa điểm:</label>
                <select
                  value={appealTarget}
                  onChange={(e) => setAppealTarget(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white"
                >
                  {students.map((s) => (
                    <option key={s.student_code} value={s.student_code}>
                      {s.student_code} - {s.full_name} (Cuối kỳ: {s.final_exam})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-400">Điểm đề nghị sửa mới:</label>
                <input
                  type="number"
                  step="0.5"
                  value={proposedScore}
                  onChange={(e) => setProposedScore(parseFloat(e.target.value) || 0)}
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-white"
                />
              </div>
            </div>
            <div>
              <label className="block text-slate-400">Lý do giải trình & Minh chứng bài thi gốc:</label>
              <input
                type="text"
                value={appealReason}
                onChange={(e) => setAppealReason(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-white"
              />
            </div>
            <button
              onClick={() => onCreateMakerAppeal(appealTarget, 6.5, proposedScore, appealReason)}
              className="w-full rounded-xl bg-amber-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-amber-500"
            >
              📤 Gửi Đơn Phúc Khảo Maker & Ghi Vết WORM (UC-TCH-08)
            </button>
          </div>
        </div>

        {/* Homeroom & Council Docs Scope (UC-TCH-09..15) */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400">
            UC-TCH-09..15 · Sổ Đầu Bài, Lớp Chủ Nhiệm & Phạm Vi Học Liệu Hội Đồng
          </h3>
          <div className="mt-4 space-y-2.5 text-xs">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
              <div className="font-bold text-white">📘 Sổ Đầu Bài Điện Tử Lớp 12A1 (UC-TCH-01, 03)</div>
              <div className="mt-1 text-slate-400">
                Tiết 2: Nguyên hàm & Tích phân từng phần · Sĩ số: <b>44/45</b> (1 nghỉ có phép) · Xếp loại tiết học: <b>Loại A</b>
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
              <div className="font-bold text-white">📄 Đề cương ôn tập Học kỳ I môn Toán 12</div>
              <div className="mt-1 font-mono text-[11px] text-slate-400">
                Scope: CLASS_STUDENTS · SHA-256: a4b9c2d1e5f80912...
              </div>
            </div>
            {session.can_view_internal_council_docs ? (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
                <div className="font-bold text-emerald-300">
                  🔐 [NỘI BỘ HỘI ĐỒNG SƯ PHẠM] Biên bản Họp Hội đồng & Quy hoạch Đề thi
                </div>
                <div className="mt-1 text-emerald-200/80">
                  Hiển thị vì tài khoản là Giáo viên Cơ hữu (<code className="font-mono">can_view_internal_council_docs = true</code>).
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3">
                <div className="font-bold text-amber-300">
                  🔒 Đã Ẩn Tài Liệu Nội Bộ Hội Đồng Sư Phạm (UC-TCH-10)
                </div>
                <div className="mt-1 text-amber-200/80">
                  Tài khoản Giáo viên Thỉnh giảng bị giới hạn theo thời hạn hợp đồng và không nhìn thấy tài liệu nội bộ hội đồng.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
