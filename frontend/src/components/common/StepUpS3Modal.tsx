import React, { useState } from 'react';

interface StepUpS3ModalProps {
  isOpen: boolean;
  actionContext: string;
  onClose: () => void;
  onConfirmStepUp: (method: 'SOFT_HSM_S3' | 'FIDO2_PKI_S3', pin: string) => void;
}

export const StepUpS3Modal: React.FC<StepUpS3ModalProps> = ({
  isOpen,
  actionContext,
  onClose,
  onConfirmStepUp,
}) => {
  const [method, setMethod] = useState<'SOFT_HSM_S3' | 'FIDO2_PKI_S3'>('SOFT_HSM_S3');
  const [pin, setPin] = useState('888888');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-purple-500/40 bg-slate-900 p-6 shadow-2xl shadow-purple-950/50">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <span className="rounded-full bg-purple-500/20 px-2.5 py-0.5 text-xs font-bold text-purple-300">
              UC-02 · Step-Up Authentication (ACR = S3)
            </span>
            <h3 className="mt-1 text-lg font-bold text-white">
              Xác Thực Chữ Ký Số Bảo Mật Cấp Độ 3
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4 text-sm">
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
            <p className="font-semibold">Chốt chặn API Gateway (PEP):</p>
            <p className="mt-0.5">
              Thao tác <code className="font-mono text-amber-100">{actionContext}</code> yêu cầu nâng cấp phiên từ{' '}
              <b>ACR=S2</b> lên <b>ACR=S3</b> (Chuẩn FIPS 140-2 Level 3 / TCVN 11930:2017).
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-400">
              Phương thức ký số phần cứng
            </label>
            <div className="mt-1.5 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setMethod('SOFT_HSM_S3')}
                className={`rounded-xl border p-2.5 text-left text-xs font-semibold transition ${
                  method === 'SOFT_HSM_S3'
                    ? 'border-purple-500 bg-purple-500/20 text-white'
                    : 'border-slate-800 bg-slate-950 text-slate-400'
                }`}
              >
                <div>🔐 Soft-HSM PKI</div>
                <div className="mt-0.5 text-[11px] font-normal opacity-80">Chứng thư số nhà trường</div>
              </button>
              <button
                type="button"
                onClick={() => setMethod('FIDO2_PKI_S3')}
                className={`rounded-xl border p-2.5 text-left text-xs font-semibold transition ${
                  method === 'FIDO2_PKI_S3'
                    ? 'border-purple-500 bg-purple-500/20 text-white'
                    : 'border-slate-800 bg-slate-950 text-slate-400'
                }`}
              >
                <div>🔑 FIDO2 / Passkey</div>
                <div className="mt-0.5 text-[11px] font-normal opacity-80">Khóa cứng YubiKey / Sinh trắc</div>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-slate-400">
              Mã PIN Soft-HSM / Khóa Bí Mật
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-white focus:border-purple-500 focus:outline-none"
              placeholder="Nhập mã PIN 6 số..."
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
            >
              Hủy bỏ
            </button>
            <button
              type="button"
              onClick={() => onConfirmStepUp(method, pin)}
              className="rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-indigo-500"
            >
              Ký Số S3 & Xác Nhận
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
