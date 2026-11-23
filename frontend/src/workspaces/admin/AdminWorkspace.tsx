import React from 'react';
import { UserSession, WormAuditEntry, PRESET_ACCOUNTS } from '../../services/api';

interface AdminWorkspaceProps {
  session: UserSession;
  wormLogs: WormAuditEntry[];
  onTestSod01Violation: () => void;
  onTestWormTamperViolation: () => void;
}

export const AdminWorkspace: React.FC<AdminWorkspaceProps> = ({
  wormLogs,
  onTestSod01Violation,
  onTestWormTamperViolation,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-slate-900 to-slate-900 p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <span className="rounded-full bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-300">
              PH2 · Phân Hệ Quản Trị Hệ Thống (UC-ADM-01..16)
            </span>
            <h2 className="mt-2 text-xl font-bold text-white">
              Quản Trị Hạ Tầng, Phân Quyền Kiêm Nhiệm & Nhật Ký Bất Biến WORM
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Tuân thủ nghiêm ngặt <b>SoD-01</b> (Admin bị cách ly tuyệt đối khỏi dữ liệu điểm số) và <b>SoD-03</b> (Chỉ đọc trên bảng WORM Audit).
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onTestSod01Violation}
              className="rounded-xl border border-rose-500/50 bg-rose-500/15 px-3.5 py-2 text-xs font-bold text-rose-200 hover:bg-rose-500/25"
            >
              🛡️ Thử Sửa Điểm Từ Góc Admin (Test Chặn SoD-01)
            </button>
            <button
              onClick={onTestWormTamperViolation}
              className="rounded-xl border border-amber-500/50 bg-amber-500/15 px-3.5 py-2 text-xs font-bold text-amber-200 hover:bg-amber-500/25"
            >
              🔒 Thử Xóa Nhật Ký WORM (Test Chặn SoD-03)
            </button>
          </div>
        </div>
      </div>

      {/* Academic Config & External Gateways */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400">
            UC-ADM-01..04 · Cấu Hình Năm Học & Biểu Điểm
          </h3>
          <div className="mt-4 space-y-3 text-xs">
            <div className="flex justify-between rounded-xl bg-slate-950 p-3">
              <span className="text-slate-400">Năm học hiện hành:</span>
              <span className="font-bold text-white">2026 - 2027 (Học kỳ I)</span>
            </div>
            <div className="flex justify-between rounded-xl bg-slate-950 p-3">
              <span className="text-slate-400">Hạn khóa sổ điểm S3:</span>
              <span className="font-mono font-semibold text-emerald-400">20/12/2026 23:59</span>
            </div>
            <div className="rounded-xl bg-slate-950 p-3">
              <div className="font-semibold text-slate-300">Trọng số BR-031 (Làm tròn HALF_UP):</div>
              <div className="mt-1.5 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-slate-900 p-2">
                  <div className="text-slate-400">Thường xuyên</div>
                  <div className="text-sm font-bold text-sky-400">Hệ số 1</div>
                </div>
                <div className="rounded-lg bg-slate-900 p-2">
                  <div className="text-slate-400">Giữa kỳ</div>
                  <div className="text-sm font-bold text-sky-400">Hệ số 2</div>
                </div>
                <div className="rounded-lg bg-slate-900 p-2">
                  <div className="text-slate-400">Cuối kỳ</div>
                  <div className="text-sm font-bold text-sky-400">Hệ số 3</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* User Roles & No Role Duplication */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-400">
              UC-ADM-05..08 · Quản Trị Tài Khoản & Gán Vai Trò (Không Nhân Bản Role Rác)
            </h3>
            <span className="rounded-lg bg-sky-500/10 px-2.5 py-1 text-xs font-semibold text-sky-300">
              4 Core Roles + Workspace Switcher
            </span>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2">Tài khoản SSO</th>
                  <th className="pb-2">Họ tên & Chức danh</th>
                  <th className="pb-2">Vai trò được gán (user_roles)</th>
                  <th className="pb-2">Định danh VNeID</th>
                  <th className="pb-2">Phạm vi lớp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {Object.values(PRESET_ACCOUNTS).map((u) => (
                  <tr key={u.username} className="hover:bg-slate-800/30">
                    <td className="py-2.5 font-mono font-semibold text-sky-300">{u.username}</td>
                    <td className="py-2.5 text-white">{u.full_name}</td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {u.roles.map((r) => (
                          <span
                            key={r}
                            className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-emerald-300"
                          >
                            {r}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 font-mono text-slate-400">{u.vneid_identifier}</td>
                    <td className="py-2.5 text-slate-300">
                      {u.assigned_classes.length > 0 ? u.assigned_classes.join(', ') : 'Toàn trường'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* WORM Chained HMAC Audit Logs (UC-08, UC-ADM-13) */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-400">
              UC-08 / UC-ADM-13 · Kho Nhật Ký Kiểm Toán Bất Biến WORM (HMAC-SHA256 Chained Audit DB)
            </h3>
            <p className="text-xs text-slate-400">
              Mỗi bản ghi liên kết mật mã với bản ghi liền trước (<code className="text-sky-300">prev_hmac_hash → entry_hmac_hash</code>). Đã thu hồi quyền UPDATE/DELETE (SoD-03).
            </p>
          </div>
          <span className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-300">
            Chuỗi Băm Toàn Vẹn: {wormLogs.length} khối
          </span>
        </div>

        <div className="mt-4 space-y-2.5">
          {wormLogs.map((log) => (
            <div
              key={log.id}
              className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 text-xs transition hover:border-slate-700"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-emerald-500/20 px-2 py-0.5 font-mono font-bold text-emerald-300">
                    #{log.id}
                  </span>
                  <span className="font-bold text-white">{log.use_case_code}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-sky-300">
                    {log.action_type}
                  </span>
                  <span className="text-slate-400">
                    Phân hệ: <b>{log.subsystem_code}</b> · Scope: <b>{log.actor_role}</b> · ACR: <b>{log.acr_level}</b>
                  </span>
                </div>
                <span className="font-mono text-[11px] text-slate-500">{log.created_at}</span>
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2 font-mono text-[11px] text-slate-400 md:grid-cols-2">
                <div className="truncate rounded bg-slate-900 px-2.5 py-1">
                  <span className="text-slate-500">prev_hmac: </span>
                  {log.prev_hmac_hash}
                </div>
                <div className="truncate rounded bg-slate-900 px-2.5 py-1 text-emerald-300">
                  <span className="text-slate-500">entry_hmac: </span>
                  {log.entry_hmac_hash}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
