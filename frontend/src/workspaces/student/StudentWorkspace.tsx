import React from 'react';
import { UserSession } from '../../services/api';

interface StudentWorkspaceProps {
  session: UserSession;
  attemptsUsed: number;
  maxAttempts: number;
  tuitionPaid: boolean;
  onSubmitAssignment: () => void;
  onPayTuitionVnpay: () => void;
  onTestStudentIdorViolation: () => void;
}

export const StudentWorkspace: React.FC<StudentWorkspaceProps> = ({
  attemptsUsed,
  maxAttempts,
  tuitionPaid,
  onSubmitAssignment,
  onPayTuitionVnpay,
  onTestStudentIdorViolation,
}) => {
  return (
    <div className="space-y-6">
      {/* Student Anti-IDOR Banner */}
      <div className="rounded-2xl border border-sky-500/30 bg-gradient-to-r from-sky-500/15 via-slate-900 to-slate-900 p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <span className="rounded-full bg-sky-500/20 px-3 py-1 text-xs font-bold text-sky-300">
              PH5 · Góc Học Tập & Dịch Vụ Người Học (UC-STU-01..13)
            </span>
            <h2 className="mt-2 text-xl font-bold text-white">
              Hồ Sơ Học Sinh: Nguyễn Hải An (Mã HS001 — Lớp 12A1)
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Chốt chặn <b>Gateway Anti-IDOR Guard</b>: Cưỡng chế <code className="text-sky-300">student_id == token.sub</code>. Mọi nỗ lực đổi tham số sang <code className="text-rose-300">studentCode=HS002</code> đều bị chặn 403 Forbidden.
            </p>
          </div>
          <button
            onClick={onTestStudentIdorViolation}
            className="rounded-xl border border-rose-500/50 bg-rose-500/15 px-4 py-2 text-xs font-bold text-rose-200 hover:bg-rose-500/25"
          >
            🕵️ Thử Xem Điểm Của HS002 (Test Chặn 403 Student Anti-IDOR)
          </button>
        </div>
      </div>

      {/* Personal Academic Results & Homework Late Penalty (Hình 9 - Sequence 5.3) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Assignment Submission with Late Penalty & SHA-256 */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400">
              UC-20 / UC-STU-07 · Nộp Bài Tập (Kiểm Soát Lượt Nộp & Phạt Nộp Muộn)
            </h3>
            <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-bold text-amber-300">
              Lượt nộp: {attemptsUsed} / {maxAttempts}
            </span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5">
              <div className="font-bold text-white">
                Bài tập #45: Chuyên đề Tích phân & Ứng dụng hình học
              </div>
              <div className="mt-1 text-slate-400">
                Hạn nộp chuẩn (Deadline): <span className="text-rose-400">23:59:59 (10/11)</span> · Thời điểm máy chủ: <span className="text-amber-300">00:30:00 (11/11 — Trễ 30 phút)</span>
              </div>
              <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-200">
                <div>⚡ <b>Quy tắc Hình 9 (Sequence 5.3)</b>:</div>
                <div className="mt-0.5">
                  • Nộp trễ 30 phút → Tự động gắn cờ <code className="font-mono">is_late = TRUE</code> và trừ <b>10% tổng điểm</b> (Điểm gốc 9.0 → Thực nhận <b>8.1</b>).
                </div>
                <div>
                  • Tệp lưu vào MinIO/S3 kèm mã băm <code className="font-mono">SHA-256</code> chống tráo bài. Nếu vượt quá {maxAttempts} lượt nộp → Chặn <b>400 Bad Request</b>.
                </div>
              </div>
            </div>

            <button
              onClick={onSubmitAssignment}
              className="w-full rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-600/25 hover:from-sky-500 hover:to-blue-500"
            >
              📤 Tải Lên Bài Tập Lần {attemptsUsed + 1} (Test Tính Phạt Muộn & Giới Hạn {maxAttempts} Lượt)
            </button>
          </div>
        </div>

        {/* Tuition Fee & VNPAY/MoMo Webhook HMAC-SHA256 (UC-21, UC-STU-11..13) */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">
              UC-21 / UC-STU-11..13 · Công Nợ Học Phí & Cổng Thanh Toán VNPAY/MoMo
            </h3>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                tuitionPaid ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
              }`}
            >
              {tuitionPaid ? 'ĐÃ HOÀN TẤT HỌC PHÍ' : 'CÒN CÔNG NỢ HK1'}
            </span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5">
              <div className="flex justify-between">
                <span className="text-slate-400">Mã hóa đơn:</span>
                <span className="font-mono font-bold text-white">INV-2026-HK1-HS001</span>
              </div>
              <div className="mt-2 flex justify-between">
                <span className="text-slate-400">Tổng học phí Học kỳ I:</span>
                <span className="font-semibold text-white">4,500,000 VNĐ</span>
              </div>
              <div className="mt-2 flex justify-between">
                <span className="text-slate-400">Còn phải nộp:</span>
                <span className="text-sm font-black text-emerald-400">
                  {tuitionPaid ? '0 VNĐ' : '1,500,000 VNĐ'}
                </span>
              </div>
              <div className="mt-2 border-t border-slate-800 pt-2 font-mono text-[11px] text-slate-400">
                Webhook đối soát: HMAC-SHA256 · Biên lai điện tử: EREC-VNPAY-2026-8812
              </div>
            </div>

            <button
              onClick={onPayTuitionVnpay}
              disabled={tuitionPaid}
              className="w-full rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-bold text-white shadow-md hover:bg-emerald-500 disabled:opacity-50"
            >
              {tuitionPaid
                ? '✅ Đã Thanh Toán & Xuất Biên Lai Điện Tử S3'
                : '💳 Thanh Toán Học Phí Qua VNPAY / MoMo (Yêu Cầu Xác Thực S2)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
