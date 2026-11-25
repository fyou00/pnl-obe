import { Link } from 'react-router-dom';
import AnimatedNavIcon from '../icons/AnimatedNavIcon.jsx';

export function LoadingSkeleton({ variant = 'dashboard', className = '' }) {
  if (variant === 'table') {
    return (
      <div
        role="status"
        aria-label="Memuat data tabel"
        className={`bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4 ${className}`.trim()}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="obe-skeleton h-5 w-48 rounded-[6px]" />
          <div className="obe-skeleton h-9 w-36 rounded-[8px]" />
        </div>
        <div className="flex flex-col gap-2.5 pt-2">
          {[0, 1, 2, 3, 4].map((row) => (
            <div
              key={row}
              className="obe-skeleton h-10 w-full rounded-[8px]"
            />
          ))}
        </div>
      </div>
    );
  }

  if (variant === 'cards') {
    return (
      <div
        role="status"
        aria-label="Memuat daftar kartu"
        className={`grid grid-cols-1 md:grid-cols-3 gap-6 ${className}`.trim()}
      >
        {[0, 1, 2].map((card) => (
          <div
            key={card}
            className="bg-white border border-[#E4DFD4] rounded-[12px] p-5 flex flex-col gap-3"
          >
            <div className="obe-skeleton h-4 w-24 rounded-[6px]" />
            <div className="obe-skeleton h-6 w-3/4 rounded-[6px]" />
            <div className="obe-skeleton h-4 w-1/2 rounded-[6px]" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-label="Memuat dashboard"
      className={`flex flex-col gap-6 ${className}`.trim()}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {[0, 1, 2, 3].map((kpi) => (
          <div
            key={kpi}
            className="min-h-[120px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between"
          >
            <div className="obe-skeleton h-3.5 w-28 rounded-[6px]" />
            <div className="obe-skeleton h-8 w-20 rounded-[6px]" />
            <div className="obe-skeleton h-3 w-36 rounded-[6px]" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
          <div className="obe-skeleton h-5 w-48 rounded-[6px]" />
          <div className="obe-skeleton h-[220px] w-full rounded-[10px]" />
        </div>
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-3">
          <div className="obe-skeleton h-5 w-44 rounded-[6px]" />
          {[0, 1, 2, 3].map((item) => (
            <div
              key={item}
              className="obe-skeleton h-11 w-full rounded-[8px]"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function LockedPeriodBanner({ period, className = '' }) {
  if (!period || (period.status !== 'Ditutup' && period.status_periode !== 'Ditutup')) {
    return null;
  }

  return (
    <div
      role="status"
      className={`rounded-[10px] bg-[#F7EAE1] border border-[#E8B899] px-4 py-3 flex items-start gap-3 text-[13px] leading-[19px] text-[#9A4213] ${className}`.trim()}
    >
      <span className="mt-0.5 shrink-0">
        <AnimatedNavIcon name="lock" active size={17} />
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[#9A4213]">
          Periode {period.tahun_akademik} {period.semester} berstatus Ditutup (Mode Read-Only)
        </p>
        <p className="text-[12.5px] text-[#B55824] mt-0.5">
          Perubahan paket, peserta, struktur rancangan penilaian, dan pengubahan nilai dikunci pada periode ini. Data historis dan ekspor laporan tetap dapat diakses secara baca-saja.
        </p>
      </div>
    </div>
  );
}

export function EmptyTikState({
  period,
  classLabel = 'TI-K',
  studentStatus = 'Cuti',
  hasOtherPeriods = false,
}) {
  return (
    <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-8 flex flex-col items-start gap-4">
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F7EAE1] border border-[#E8B899] text-[12px] font-semibold text-[#B55824]">
        <AnimatedNavIcon name="info" active size={15} />
        <span>
          {classLabel} · Status {studentStatus}
        </span>
      </div>

      <div className="max-w-[640px]">
        <h2 className="text-[20px] font-semibold leading-[28px] text-[#15333A]">
          Tidak ada mata kuliah paket pada periode ini
        </h2>
        <p className="text-[14px] leading-[22px] text-[#566B70] mt-2">
          Pada periode{' '}
          <strong className="text-[#15333A]">
            {period
              ? `${period.tahun_akademik} ${period.semester}`
              : 'terpilih'}
          </strong>
          , Anda tercatat pada kelas khusus <strong>{classLabel}</strong> dengan
          status <strong>{studentStatus}</strong>. Kelas TI-K tidak menerima
          paket mata kuliah sehingga tidak ada instrumen atau nilai buatan
          (0,00%) yang ditampilkan.
        </p>
      </div>

      {hasOtherPeriods && (
        <p className="text-[13px] text-[#1A5C4D] bg-[#E6F2EE] border border-[#C6DFD7] rounded-[8px] px-3.5 py-2.5">
          Gunakan pemilih <strong>Periode akademik</strong> di bilah atas atau
          aktifkan mode <strong>Kumulatif</strong> pada menu Capaian CPL untuk
          meninjau riwayat capaian dari periode aktif sebelumnya.
        </p>
      )}
    </section>
  );
}

export function AccessDeniedState({ role, homePath = '/' }) {
  return (
    <main className="min-h-screen bg-[#FAF8F3] text-[#15333A] flex items-center justify-center px-6 py-12">
      <section className="max-w-[460px] w-full bg-white border border-[#E4DFD4] rounded-[14px] p-8 shadow-[0_8px_24px_rgba(21,51,58,0.06)] flex flex-col gap-5">
        <div className="inline-flex items-center self-start gap-2 px-3 py-1 rounded-full bg-[#FEF3F2] border border-[#FECDCA] text-[12px] font-semibold text-[#B42318]">
          <span>403 · Akses Ditolak</span>
        </div>

        <div>
          <h1 className="text-[22px] font-semibold leading-[30px] text-[#15333A]">
            Halaman tidak tersedia untuk peran Anda
          </h1>
          <p className="text-[14px] leading-[22px] text-[#566B70] mt-2">
            Anda masuk sebagai <strong className="text-[#15333A]">{role}</strong>
            . Pembatasan RBAC PNL OBE memisahkan ruang kerja Admin/Kaprodi,
            Dosen Pengampu, dan Mahasiswa secara ketat.
          </p>
        </div>

        <Link
          to={homePath}
          className="h-10 px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[13.5px] font-semibold inline-flex items-center justify-center self-start transition-colors"
        >
          Kembali ke ruang kerja {role}
        </Link>
      </section>
    </main>
  );
}

export function SessionExpiredBanner({ onDismiss }) {
  return (
    <div
      role="alert"
      className="rounded-[9px] bg-[#F7EAE1] border border-[#E8B899] px-3.5 py-2.5 flex items-start justify-between gap-3 text-[13px] leading-[19px] text-[#9A4213]"
    >
      <div>
        <p className="font-semibold">401 · Sesi Anda telah berakhir</p>
        <p className="text-[12px] text-[#B55824] mt-0.5">
          Token autentikasi kedaluwarsa atau telah dicabut. Silakan masuk
          kembali untuk melanjutkan.
        </p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-[12px] font-semibold text-[#9A4213] hover:underline shrink-0 cursor-pointer"
        >
          Tutup
        </button>
      )}
    </div>
  );
}
