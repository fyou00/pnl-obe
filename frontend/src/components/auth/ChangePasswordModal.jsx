import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';

function utf8ByteLength(value) {
  return new TextEncoder().encode(value).length;
}

export default function ChangePasswordModal({ open, onClose }) {
  const { changePassword } = useAuth();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (!open) return;
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setShowPasswords(false);
    setError('');
    setSuccessMessage('');
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape' && !submitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose, submitting]);

  if (!open) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccessMessage('');

    if (!currentPassword) {
      setError('Masukkan kata sandi saat ini.');
      return;
    }
    const newBytes = utf8ByteLength(newPassword);
    if (newBytes < 12 || newBytes > 72) {
      setError('Kata sandi baru harus terdiri dari 12–72 byte UTF-8.');
      return;
    }
    if (newPassword === currentPassword) {
      setError('Kata sandi baru harus berbeda dari kata sandi saat ini.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Konfirmasi kata sandi baru tidak cocok.');
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setSuccessMessage(
        'Kata sandi berhasil diperbarui. Sesi pada perangkat lain telah dicabut.',
      );
    } catch (err) {
      setError(err.message || 'Gagal memperbarui kata sandi.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-[#15333A]/40 flex items-center justify-center p-4"
      onClick={() => {
        if (!submitting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-pw-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[460px] bg-white border border-[#E4DFD4] rounded-[14px] p-6 shadow-[0_16px_40px_rgba(21,51,58,0.14)] flex flex-col gap-5"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="change-pw-title"
              className="text-[20px] font-semibold text-[#15333A]"
            >
              Ganti Kata Sandi
            </h2>
            <p className="text-[13px] text-[#566B70] mt-1">
              Minimal 12 karakter (maksimal 72 byte). Sesi lain akan otomatis
              keluar.
            </p>
          </div>
          <button
            type="button"
            disabled={submitting}
            onClick={onClose}
            className="h-8 px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium text-[#566B70] hover:text-[#15333A] cursor-pointer disabled:opacity-50"
          >
            Tutup
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-[9px] bg-[#FEF3F2] border border-[#FECDCA] px-3.5 py-2.5 text-[13px] text-[#B42318]"
          >
            {error}
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="rounded-[9px] bg-[#E6F2EE] border border-[#C6DFD7] px-3.5 py-2.5 text-[13px] text-[#1A5C4D]"
          >
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5" noValidate>
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="cp-current"
              className="text-[12.5px] font-medium text-[#334B51]"
            >
              Kata sandi saat ini
            </label>
            <input
              id="cp-current"
              type={showPasswords ? 'text' : 'password'}
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={submitting}
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] text-[#15333A]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="cp-new"
              className="text-[12.5px] font-medium text-[#334B51]"
            >
              Kata sandi baru
            </label>
            <input
              id="cp-new"
              type={showPasswords ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Minimal 12 karakter"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={submitting}
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] text-[#15333A]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="cp-confirm"
              className="text-[12.5px] font-medium text-[#334B51]"
            >
              Konfirmasi kata sandi baru
            </label>
            <input
              id="cp-confirm"
              type={showPasswords ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Ulangi kata sandi baru"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={submitting}
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] text-[#15333A]"
            />
          </div>

          <label className="inline-flex items-center gap-2 text-[12.5px] text-[#566B70] cursor-pointer w-fit">
            <input
              type="checkbox"
              checked={showPasswords}
              onChange={(e) => setShowPasswords(e.target.checked)}
              className="accent-[#15333A]"
            />
            <span>Tampilkan kata sandi</span>
          </label>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              disabled={submitting}
              onClick={onClose}
              className="h-[38px] px-4 rounded-[8px] border border-[#E4DFD4] text-[13px] font-medium text-[#334B51] hover:bg-[#FAF8F3] cursor-pointer disabled:opacity-50"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="h-[38px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[13px] font-semibold cursor-pointer disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Menyimpan...' : 'Simpan Kata Sandi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
