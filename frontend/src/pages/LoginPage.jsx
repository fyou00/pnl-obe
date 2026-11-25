import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { getHomeRouteForRole } from '../components/auth/ProtectedRoute.jsx';
import { SessionExpiredBanner } from '../components/states/SystemStates.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function LoginPage() {
  const { user, status, sessionExpired, clearSessionExpired, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (status === 'authenticated' && user) {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    if (!email.trim() || !password) {
      setErrorMessage('Masukkan email institusi dan kata sandi.');
      return;
    }

    setSubmitting(true);
    try {
      const profile = await login(email, password);
      navigate(getHomeRouteForRole(profile.role), { replace: true });
    } catch (err) {
      setErrorMessage(
        err.message || 'Autentikasi gagal. Periksa kembali kredensial Anda.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#FAF8F3] text-[#15333A] flex flex-col justify-between px-[72px] py-12">
      <header className="max-w-[1296px] w-full mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-[8px] bg-[#15333A] flex items-center justify-center text-[#FAF8F3] font-bold text-[16px] leading-none">
            O
          </span>
          <span className="text-[18px] font-bold tracking-[-0.01em] text-[#15333A]">
            PNL OBE
          </span>
          <span className="w-px h-[18px] bg-[#B9C5C3]" aria-hidden="true" />
          <span className="text-[13px] font-medium text-[#486065]">
            Teknik Informatika
          </span>
        </Link>

        <Link
          to="/"
          className="text-[14px] font-medium text-[#1D373E] hover:text-[#CC6E38] transition-colors"
        >
          ← Kembali ke beranda
        </Link>
      </header>

      <section className="max-w-[480px] w-full mx-auto bg-white border border-[#E4DFD4] rounded-[16px] p-9 shadow-[0_8px_24px_rgba(21,51,58,0.06)] flex flex-col gap-6">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-[10px]">
            <span
              className="w-6 h-[2px] rounded-[1px] bg-[#CC6E38] shrink-0"
              aria-hidden="true"
            />
            <span className="text-[12px] font-bold tracking-[0.08em] text-[#4A6065]">
              AKSES AKUN PNL
            </span>
          </div>

          <h1 className="font-serif font-normal text-[36px] leading-[44px] text-[#132F36]">
            Masuk ke ruang kerja OBE.
          </h1>

          <p className="text-[14.5px] leading-[22px] text-[#486065]">
            Gunakan email institusi dan kata sandi yang terdaftar sesuai peran
            Admin / Kaprodi, Dosen, atau Mahasiswa.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          {sessionExpired && (
            <SessionExpiredBanner onDismiss={clearSessionExpired} />
          )}

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="login-email"
              className="text-[13px] font-medium text-[#15333A]"
            >
              Email institusi
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nama@pnl.ac.id"
              className="h-11 px-3.5 rounded-[9px] bg-[#FAF8F3] border border-[#DDD8CC] text-[14px] text-[#15333A] placeholder:text-[#8B9D9B] focus:outline-none focus:border-[#15333A] focus:bg-white transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="login-password"
              className="text-[13px] font-medium text-[#15333A]"
            >
              Kata sandi
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan kata sandi"
                className="w-full h-11 pl-3.5 pr-24 rounded-[9px] bg-[#FAF8F3] border border-[#DDD8CC] text-[14px] text-[#15333A] placeholder:text-[#8B9D9B] focus:outline-none focus:border-[#15333A] focus:bg-white transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 px-2 py-1 text-[12px] font-medium text-[#486065] hover:text-[#15333A] cursor-pointer"
              >
                {showPassword ? 'Sembunyikan' : 'Tampilkan'}
              </button>
            </div>
          </div>

          {errorMessage && (
            <div
              role="alert"
              className="rounded-[9px] bg-[#F7EAE1] border border-[#E8B899] px-3.5 py-2.5 text-[13px] leading-[19px] text-[#9A4213]"
            >
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || status === 'loading'}
            className="mt-1 h-12 rounded-[10px] bg-[#15333A] hover:bg-[#1D434B] disabled:opacity-60 transition-colors px-5 inline-flex items-center justify-center gap-2 text-[15px] font-semibold text-white cursor-pointer"
          >
            <span>{submitting ? 'Memverifikasi...' : 'Masuk ke PNL OBE'}</span>
            {!submitting && (
              <span className="text-[#F0C3A4]" aria-hidden="true">
                ↗
              </span>
            )}
          </button>
        </form>

        <div className="border-t border-[#EFECE4] pt-4 text-[12.5px] leading-[19px] text-[#5A6F73]">
          Tidak tersedia pendaftaran akun publik. Akses dan cakupan data diatur
          berdasarkan peran akun (RBAC) dan pencabutan sesi tersinkron dengan
          server.
        </div>
      </section>

      <footer className="max-w-[1296px] w-full mx-auto border-t border-[#E3DDD1] pt-5 flex items-center justify-between text-[13.5px] text-[#5A6F73]">
        <span>PNL OBE · Pengukuran Capaian Pembelajaran Lulusan</span>
        <span>Program Studi Teknik Informatika · Politeknik Negeri Lhokseumawe</span>
      </footer>
    </main>
  );
}
