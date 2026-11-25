import BackendPendingNotice from '../../components/dashboard/BackendPendingNotice.jsx';

const PAGE_CONFIG = {
  pengguna: {
    heading: 'Pengguna',
    subtitle: 'Kelola akun Admin / Kaprodi, Dosen, dan Mahasiswa dalam prodi.',
    noticeTitle: 'Manajemen Pengguna menunggu endpoint backend',
    description:
      'Backend saat ini baru menyediakan daftar Dosen aktif (GET /api/v1/dosen) untuk penugasan paket. Endpoint daftar semua pengguna, pembuatan akun, ubah peran, dan aktivasi akun belum tersedia.',
    missingEndpoints: [
      'GET /api/v1/users (daftar akun Admin, Dosen, Mahasiswa beserta filter peran/status).',
      'POST /api/v1/users & PATCH /api/v1/users/{id} (registrasi internal terkelola Admin, ubah peran, nonaktifkan akun).',
    ],
  },
  laporan: {
    heading: 'Laporan OBE',
    subtitle:
      'Rekap ketercapaian CPMK, CPL per periode, serta ekspor CSV/PDF resmi.',
    noticeTitle: 'Laporan & Kalkulasi OBE menunggu endpoint backend',
    description:
      'Sesuai AGENTS.md, seluruh kalkulasi capaian OBE (Decimal) dan ekspor laporan dilakukan di Backend Service Layer. Endpoint agregasi capaian dan unduh CSV/PDF belum tersedia.',
    missingEndpoints: [
      'Service & endpoint kalkulasi agregat persentase capaian Sub-CPMK, CPMK, dan CPL.',
      'Endpoint ekspor laporan rekap nilai & capaian OBE format CSV/PDF.',
      'Endpoint penutupan dan pembukaan kembali periode beserta riwayat audit.',
    ],
  },
};

export default function AdminBackendPendingPage({ section }) {
  const config = PAGE_CONFIG[section] || PAGE_CONFIG.laporan;

  return (
    <div className="max-w-[920px] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
          {config.heading}
        </h1>
        <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
          {config.subtitle}
        </p>
      </div>

      <BackendPendingNotice
        title={config.noticeTitle}
        description={config.description}
        missingEndpoints={config.missingEndpoints}
      />
    </div>
  );
}
