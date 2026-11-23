import React from 'react';
import { GradeAppealItem, UserSession } from '../../services/api';

interface BoardWorkspaceProps {
  session: UserSession;
  appeals: GradeAppealItem[];
  onApproveAppealChecker: (appealCode: string, simulateSelfApprovalSod02: boolean) => void;
  onSignTranscriptS3: () => void;
}

export const BoardWorkspace: React.FC<BoardWorkspaceProps> = ({
  session,
  appeals,
  onApproveAppealChecker,
  onSignTranscriptS3,
}) => {
  return (
    <div className="space-y-6">
      {/* Executive Header */}
      <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-r from-purple-500/15 via-slate-900 to-slate-900 p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <span className="rounded-full bg-purple-500/20 px-3 py-1 text-xs font-bold text-purple-300">
              PH6 & PH4 · Góc Điều Hành Ban Lãnh Đạo (UC-BRD-01..14)
            </span>
            <h2 className="mt-2 text-xl font-bold text-white">
              Dashboard Giám Sát Toàn Trường, Duyệt Phúc Khảo Maker-Checker & Ký Số Học Bạ S3
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Đang hoạt động với ngữ cảnh <code className="text-purple-300">X-Workspace-Context: BOARD</code>. Mọi phê duyệt mở khóa điểm bắt buộc <b>ACR=S3</b> và <b>SoD-02 (Maker ≠ Checker)</b>.
            </p>
          </div>
          <button
            onClick={onSignTranscriptS3}
            className="rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-indigo-500"
          >
            ✍️ Ký Số Học Bạ Điện Tử & Đồng Bộ MOET (UC-BRD-07)
          </button>
        </div>
      </div>

      {/* KPI Cards (UC-BRD-01..03) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-xs text-slate-400">Tổng sĩ số & Chuyên cần hôm nay</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-white">1,240 HS</span>
            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-bold text-emerald-400">
              98.4% Có mặt
            </span>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-xs text-slate-400">Tiến độ khóa sổ điểm S3</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-sky-400">38 / 42 Lớp</span>
            <span className="text-xs text-slate-400">90.5% Hoàn tất</span>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-xs text-slate-400">Tỷ lệ Học lực Giỏi / Khá</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-black text-purple-400">42.5% / 38%</span>
            <span className="text-xs text-emerald-400">Chuẩn BR-031</span>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-xs text-slate-400">Liên thông CSDL Bộ GD&ĐT (MOET)</div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-lg font-bold text-emerald-400">ĐÃ ĐỒNG BỘ XML</span>
            <span className="text-xs text-slate-400">UC-BRD-14</span>
          </div>
        </div>
      </div>

      {/* Maker-Checker Grade Appeals Table (Hình 8 - Sequence 5.2) */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-purple-400">
              UC-11 / UC-BRD-06 · Thẩm Định & Phê Duyệt Mở Khóa Sửa Điểm (Checker - Mở Cửa Sổ 24 Giờ)
            </h3>
            <p className="text-xs text-slate-400">
              Ràng buộc CSDL: <code className="text-amber-300">CHECK (maker_id &lt;&gt; checker_id)</code>. Nếu Phó Hiệu trưởng kiêm GV Toán tự bấm duyệt đơn do chính mình tạo ở góc GV, hệ thống sẽ chặn <b>403 SoD-02</b>!
            </p>
          </div>
        </div>

        <div className="mt-4 space-y-3">
          {appeals.map((ap) => (
            <div
              key={ap.appeal_code}
              className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-xs"
            >
              <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-purple-500/20 px-2.5 py-0.5 font-mono font-bold text-purple-300">
                      {ap.appeal_code}
                    </span>
                    <span className="font-bold text-white">
                      Học sinh: {ap.student_name} ({ap.student_code}) — Lớp {ap.class_id}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 font-bold ${
                        ap.status === 'APPROVED'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {ap.status === 'APPROVED'
                        ? 'ĐÃ MỞ KHÓA 24 GIỜ (UNLOCKED_FOR_EDIT)'
                        : 'CHỜ CHECKER PHÊ DUYỆT (PENDING_APPROVAL)'}
                    </span>
                  </div>
                  <p className="text-slate-300">
                    Đề nghị sửa cột <b>{ap.score_component}</b> từ{' '}
                    <span className="font-bold text-rose-400">{ap.old_score}</span> →{' '}
                    <span className="font-bold text-emerald-400">{ap.proposed_new_score}</span> · Lý do:{' '}
                    <i>{ap.reason}</i>
                  </p>
                  <div className="flex flex-wrap gap-4 pt-1 font-mono text-[11px] text-slate-400">
                    <span>Người tạo (Maker): {ap.maker_username}</span>
                    <span>Chữ ký Maker: {ap.maker_s3_sig}</span>
                    {ap.checker_s3_sig && (
                      <span className="text-emerald-400">Chữ ký Checker S3: {ap.checker_s3_sig}</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => onApproveAppealChecker(ap.appeal_code, true)}
                    className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20"
                    title="Mô phỏng Phó HT kiêm GV tự duyệt đơn của chính mình -> Chặn SoD-02"
                  >
                    Thử Tự Duyệt Đơn Mình Tạo (Test Chặn SoD-02)
                  </button>
                  <button
                    onClick={() => onApproveAppealChecker(ap.appeal_code, false)}
                    className="rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white shadow-md hover:bg-emerald-500"
                  >
                    {session.current_acr === 'S3'
                      ? '✅ Phê Duyệt Mở Khóa 24h (Checker S3)'
                      : '🔐 Ký Số S3 & Duyệt Mở Khóa 24h'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
