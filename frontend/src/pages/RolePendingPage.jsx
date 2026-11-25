import { Navigate } from 'react-router-dom';
import { getHomeRouteForRole } from '../components/auth/ProtectedRoute.jsx';
import BackendPendingNotice from '../components/dashboard/BackendPendingNotice.jsx';
import WorkspaceShell from '../components/dashboard/WorkspaceShell.jsx';
import { useAuth } from '../context/AuthContext.jsx';

const MAHASISWA_BLOCKERS = [
  'Akses baca daftar periode akademik & status/kelas Mahasiswa (TI-1A s.d. TI-4E atau TI-K untuk Cuti/Nonaktif) — GET /api/v1/periode-akademik saat ini dibatasi untuk Admin.',
  'Endpoint metadata daftar instrumen penilaian & bobot per Sub-CPMK bagi Mahasiswa untuk menampilkan rincian nilai instrumen lengkap beserta status "Belum diinput" (GET /api/v1/kelas-mk/{id}/rancangan-penilaian saat ini dibatasi untuk Dosen).',
];

export default function RolePendingPage() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== 'Mahasiswa') {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />;
  }

  const navGroups = [
    {
      label: 'RUANG MAHASISWA',
      items: [{ to: '/ruang-kerja', label: 'Status ruang kerja', end: true }],
    },
  ];

  return (
    <WorkspaceShell
      navGroups={navGroups}
      showPeriodSelector={false}
      leftContextLabel="Ruang Kerja Mahasiswa"
    >
      <div className="max-w-[920px] flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Dashboard Mahasiswa
          </h1>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0]">
            Sesi autentikasi JWT Anda aktif. Ruang kerja Mahasiswa menunggu
            kelengkapan endpoint backend berikut agar daftar periode, kelas/status,
            dan rincian instrumen dapat dimuat dengan benar.
          </p>
        </div>

        <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
          <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
            Identitas Akun Terverifikasi
          </h2>
          <dl className="mt-4 grid grid-cols-4 gap-4 text-[13px]">
            <div>
              <dt className="text-[#737373] dark:text-[#A3A3A0]">Nama</dt>
              <dd className="mt-1 font-medium text-[#252525] dark:text-[#F5F5F4]">
                {user.nama}
              </dd>
            </div>
            <div>
              <dt className="text-[#737373] dark:text-[#A3A3A0]">NIM / NIDN</dt>
              <dd className="mt-1 font-medium text-[#252525] dark:text-[#F5F5F4]">
                {user.nim_nidn}
              </dd>
            </div>
            <div>
              <dt className="text-[#737373] dark:text-[#A3A3A0]">Email</dt>
              <dd className="mt-1 font-medium text-[#252525] dark:text-[#F5F5F4] truncate">
                {user.email}
              </dd>
            </div>
            <div>
              <dt className="text-[#737373] dark:text-[#A3A3A0]">Peran</dt>
              <dd className="mt-1 font-medium text-[#252525] dark:text-[#F5F5F4]">
                {user.role}
              </dd>
            </div>
          </dl>
        </section>

        <BackendPendingNotice
          title="Menunggu endpoint backend untuk Mahasiswa"
          description="Endpoint agregasi capaian pribadi (GET /api/v1/capaian/saya) dan baca nilai (GET /api/v1/kelas-mk/{id}/nilai) sudah tersedia di backend, namun dua konteks wajib berikut belum tersedia untuk peran Mahasiswa."
          missingEndpoints={MAHASISWA_BLOCKERS}
        />
      </div>
    </WorkspaceShell>
  );
}
