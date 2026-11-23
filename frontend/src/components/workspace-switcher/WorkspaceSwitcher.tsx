import React from 'react';
import { UserSession, WorkspaceScope, PRESET_ACCOUNTS } from '../../services/api';

interface WorkspaceSwitcherProps {
  session: UserSession;
  onSwitchWorkspace: (target: WorkspaceScope) => void;
  onSelectPresetAccount: (username: string) => void;
  onOpenStepUpModal: () => void;
  onTriggerLockoutDemo: () => void;
}

const WORKSPACE_META: Record<
  WorkspaceScope,
  { label: string; badge: string; requiredRole: string; color: string }
> = {
  ADMIN: {
    label: 'Góc Quản Trị (Admin Tier)',
    badge: 'PH2 · SoD-01',
    requiredRole: 'ROLE_ADMIN',
    color: 'from-amber-500 to-orange-600',
  },
  BOARD: {
    label: 'Góc Quản Lý (Ban Lãnh Đạo)',
    badge: 'PH6 · Checker S3',
    requiredRole: 'ROLE_BOARD',
    color: 'from-purple-500 to-indigo-600',
  },
  TEACHER: {
    label: 'Góc Giảng Dạy (Giáo Viên)',
    badge: 'PH3/PH4 · Data Scope',
    requiredRole: 'ROLE_TEACHER',
    color: 'from-emerald-500 to-teal-600',
  },
  STUDENT: {
    label: 'Góc Học Tập (Học Sinh)',
    badge: 'PH5 · Anti-IDOR',
    requiredRole: 'ROLE_STUDENT',
    color: 'from-sky-500 to-blue-600',
  },
};

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({
  session,
  onSwitchWorkspace,
  onSelectPresetAccount,
  onOpenStepUpModal,
  onTriggerLockoutDemo,
}) => {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-900/95 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {/* Brand & TCVN Badge */}
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 font-black text-white shadow-lg shadow-sky-500/20">
              AS
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">
                  AuthShield-LMS
                </h1>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                  TCVN 11930:2017 Cấp Độ 3
                </span>
                <span className="rounded-full border border-sky-500/40 bg-sky-500/10 px-2.5 py-0.5 text-xs font-semibold text-sky-300">
                  AI-Agent V2.1
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Cổng Xác Thực Đa Tầng SSO-MFA (S1/S2/S3) · Workspace Switcher · Anti-IDOR & WORM Audit
              </p>
            </div>
          </div>

          {/* Account Persona Switcher & Step-Up ACR Badge */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950 px-3 py-1.5">
              <span className="text-xs font-medium text-slate-400">Tài khoản SSO (UC-01):</span>
              <select
                aria-label="Chọn tài khoản mô phỏng"
                value={session.username}
                onChange={(e) => onSelectPresetAccount(e.target.value)}
                className="rounded-lg bg-slate-900 px-2 py-1 text-xs font-semibold text-sky-300 focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {Object.values(PRESET_ACCOUNTS).map((acc) => (
                  <option key={acc.username} value={acc.username}>
                    {acc.full_name} [{acc.roles.join(' + ')}]
                  </option>
                ))}
              </select>
            </div>

            {/* Current ACR Level Indicator */}
            <div
              className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-bold ${
                session.current_acr === 'S3'
                  ? 'border-purple-500/50 bg-purple-500/15 text-purple-200'
                  : session.current_acr === 'S2'
                  ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200'
                  : 'border-amber-500/50 bg-amber-500/15 text-amber-200'
              }`}
            >
              <span>ACR: {session.current_acr}</span>
              <span className="text-[11px] font-normal opacity-80">
                {session.current_acr === 'S3'
                  ? '(Soft-HSM / FIDO2 Đã Ký)'
                  : session.current_acr === 'S2'
                  ? '(MFA TOTP/SMS)'
                  : '(Mật khẩu S1)'}
              </span>
              {session.current_acr !== 'S3' && (
                <button
                  onClick={onOpenStepUpModal}
                  className="ml-1 rounded-lg bg-purple-600 px-2 py-0.5 text-[11px] font-semibold text-white hover:bg-purple-500"
                >
                  Step-Up S3
                </button>
              )}
            </div>

            <button
              onClick={onTriggerLockoutDemo}
              className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20"
              title="Mô phỏng nhập sai mật khẩu vượt ngưỡng -> HTTP 423 Locked (UC-01)"
            >
              Test Khóa Lũy Tiến (423)
            </button>
          </div>
        </div>

        {/* Workspace Switcher Bar (UC-04 - Hình 7 Sequence 5.1) */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800/90 bg-slate-950/90 px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              UC-04 Workspace Switcher:
            </span>
            <span className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-xs text-sky-300">
              X-Workspace-Context: {session.active_scope}
            </span>
            {session.roles.length > 1 && (
              <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300">
                Người Kiêm Nhiệm (Không nhân bản Role rác)
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(WORKSPACE_META) as WorkspaceScope[]).map((scope) => {
              const meta = WORKSPACE_META[scope];
              const hasRole = session.roles.includes(meta.requiredRole);
              const isActive = session.active_scope === scope;
              return (
                <button
                  key={scope}
                  onClick={() => onSwitchWorkspace(scope)}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                    isActive
                      ? `bg-gradient-to-r ${meta.color} text-white shadow-md`
                      : hasRole
                      ? 'border border-slate-700 bg-slate-900 text-slate-200 hover:border-sky-500/50 hover:text-white'
                      : 'border border-slate-800/80 bg-slate-900/40 text-slate-500 hover:border-rose-500/40 hover:text-rose-300'
                  }`}
                >
                  <span>{meta.label}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] ${
                      isActive ? 'bg-black/25 text-white' : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {hasRole ? meta.badge : 'Chặn 403'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </header>
  );
};
