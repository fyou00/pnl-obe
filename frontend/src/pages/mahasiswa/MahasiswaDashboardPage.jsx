import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import AnimatedNavIcon from '../../components/icons/AnimatedNavIcon.jsx';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import {
  EmptyTikState,
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';
import {
  exportMahasiswaCapaianSaya,
  getMahasiswaCapaianSaya,
} from '../../lib/mahasiswaApi.js';

export default function MahasiswaDashboardPage() {
  const { user } = useAuth();
  const {
    periods,
    selectedPeriodId,
    selectedPeriod,
    isTikOrInactive,
    classes,
    loadingWorkspace,
    workspaceError,
    refreshMahasiswaWorkspace,
  } = useMahasiswaWorkspace();

  const [kumulatif, setKumulatif] = useState(false);
  const [attainment, setAttainment] = useState(null);
  const [loadingAttainment, setLoadingAttainment] = useState(false);
  const [exporting, setExporting] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadPersonalAttainment = useCallback(async () => {
    if (!selectedPeriodId) {
      setAttainment(null);
      return;
    }
    setLoadingAttainment(true);
    setError('');
    try {
      const data = await getMahasiswaCapaianSaya(selectedPeriodId, {
        kumulatif,
      });
      setAttainment(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat ringkasan capaian CPL pribadi.');
      setAttainment(null);
    } finally {
      setLoadingAttainment(false);
    }
  }, [kumulatif, selectedPeriodId]);

  useEffect(() => {
    loadPersonalAttainment();
  }, [loadPersonalAttainment]);

  const handleExport = async (format) => {
    if (!selectedPeriodId) return;
    setExporting(format);
    setError('');
    setNotice('');
    try {
      const { filename } = await exportMahasiswaCapaianSaya(selectedPeriodId, {
        kumulatif,
        format,
      });
      setNotice(`Berkas ${filename} berhasil diunduh.`);
    } catch (err) {
      setError(err.message || `Gagal mengunduh laporan pribadi (${format}).`);
    } finally {
      setExporting('');
    }
  };

  const cplResults = attainment?.hasil || [];
  const completeCplCount = useMemo(
    () => cplResults.filter((item) => item.status === 'Lengkap').length,
    [cplResults],
  );

  const isBusy = loadingWorkspace || loadingAttainment;

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#E6F0EE] border border-[#D4E3E0] text-[11.5px] font-semibold text-[#15333A]">
            <span>Mode Read-Only · Capaian Pribadi</span>
          </div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A] mt-2">
            Dashboard Mahasiswa
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1">
            {user?.nama || 'Mahasiswa'} · NIM {user?.nim_nidn || '—'}
            {selectedPeriod
              ? ` · ${selectedPeriod.prodi_nama} · Kurikulum ${selectedPeriod.kode_kurikulum}`
              : ''}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            disabled={!selectedPeriodId || Boolean(exporting)}
            onClick={() => handleExport('csv')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-white border border-[#E4DFD4] hover:border-[#15333A] text-[12.5px] font-semibold text-[#15333A] inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" size={15} />
            <span>{exporting === 'csv' ? 'Mengunduh...' : 'Unduh CSV'}</span>
          </button>

          <button
            type="button"
            disabled={!selectedPeriodId || Boolean(exporting)}
            onClick={() => handleExport('pdf')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-[12.5px] font-semibold text-white inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" surface="dark" size={15} />
            <span>{exporting === 'pdf' ? 'Mengunduh...' : 'Unduh PDF'}</span>
          </button>
        </div>
      </div>

      <LockedPeriodBanner period={selectedPeriod} />

      {workspaceError && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 flex items-center justify-between gap-4 text-[13px] text-[#B42318]"
        >
          <span>{workspaceError}</span>
          <button
            type="button"
            onClick={refreshMahasiswaWorkspace}
            className="h-8 px-3 rounded-[7px] bg-white border border-[#FECDCA] text-[12px] font-semibold cursor-pointer"
          >
            Muat ulang
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
        >
          {error}
        </div>
      )}

      {notice && (
        <div
          role="status"
          className="rounded-[10px] bg-[#E6F2EE] border border-[#C6DFD7] px-4 py-3 text-[13px] text-[#1A5C4D]"
        >
          {notice}
        </div>
      )}

      {isBusy ? (
        <LoadingSkeleton variant="dashboard" />
      ) : !selectedPeriod ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada penempatan periode akademik untuk akun Anda. Hubungi Admin Prodi apabila roster periode belum ditetapkan.
        </div>
      ) : isTikOrInactive && !kumulatif ? (
        <EmptyTikState
          period={selectedPeriod}
          classLabel={selectedPeriod.kelas}
          studentStatus={selectedPeriod.status_mahasiswa}
          hasOtherPeriods={periods.length > 1}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="min-h-[118px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
              <span className="text-[12.5px] font-medium text-[#566B70]">
                Mata Kuliah Paket
              </span>
              <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                {classes.length}
              </span>
              <span className="text-[11px] text-[#7A8C90]">
                Ditetapkan kampus (tanpa KRS mandiri)
              </span>
            </div>

            <div className="min-h-[118px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
              <span className="text-[12.5px] font-medium text-[#566B70]">
                CPL Lengkap
              </span>
              <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                {completeCplCount} / {cplResults.length}
              </span>
              <span className="text-[11px] text-[#7A8C90]">
                {kumulatif ? 'Kumulatif hingga periode ini' : 'Periode terpilih'}
              </span>
            </div>

            <div className="min-h-[118px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
              <span className="text-[12.5px] font-medium text-[#566B70]">
                Kelas & Status
              </span>
              <span className="text-[22px] font-semibold text-[#15333A]">
                {selectedPeriod.kelas}
              </span>
              <span className="text-[11px] text-[#7A8C90]">
                Status: {selectedPeriod.status_mahasiswa}
                {selectedPeriod.semester_studi
                  ? ` · Semester ${selectedPeriod.semester_studi}`
                  : ''}
              </span>
            </div>

            <div className="min-h-[118px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
              <span className="text-[12.5px] font-medium text-[#566B70]">
                Kurikulum Angkatan
              </span>
              <span className="text-[20px] font-semibold text-[#15333A] truncate">
                {selectedPeriod.kode_kurikulum}
              </span>
              <span className="text-[11px] text-[#7A8C90]">
                Angkatan {selectedPeriod.tahun_masuk}
              </span>
            </div>
          </div>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-[18px] font-semibold text-[#15333A]">
                  Radar Capaian CPL Pribadi
                </h2>
                <p className="text-[12.5px] text-[#566B70] mt-1">
                  Capaian aktual murni tanpa garis target dan tanpa data peserta lain.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setKumulatif(false)}
                  className={[
                    'h-[32px] px-3 rounded-[7px] text-[12px] font-semibold cursor-pointer transition-colors',
                    !kumulatif
                      ? 'bg-[#15333A] text-white'
                      : 'border border-[#E4DFD4] bg-white text-[#566B70] hover:text-[#15333A]',
                  ].join(' ')}
                >
                  Periode Terpilih
                </button>
                <button
                  type="button"
                  onClick={() => setKumulatif(true)}
                  className={[
                    'h-[32px] px-3 rounded-[7px] text-[12px] font-semibold cursor-pointer transition-colors',
                    kumulatif
                      ? 'bg-[#15333A] text-white'
                      : 'border border-[#E4DFD4] bg-white text-[#566B70] hover:text-[#15333A]',
                  ].join(' ')}
                >
                  Kumulatif
                </button>
              </div>
            </div>

            <RadarCapaianChart
              items={cplResults}
              emptyMessage="Belum ada CPL terukur pada cakupan periode ini."
            />

            {cplResults.length > 0 && (
              <div className="border-t border-[#EFECE4] pt-4 grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {cplResults.map((cpl) => {
                  const pct =
                    cpl.capaian !== null && cpl.capaian !== undefined
                      ? Math.min(100, Math.max(0, Number(cpl.capaian)))
                      : null;
                  return (
                    <div
                      key={cpl.id}
                      className="p-3.5 rounded-[10px] bg-[#FAF8F3] border border-[#EFECE4] flex flex-col gap-1.5"
                    >
                      <div className="flex items-center justify-between text-[12.5px]">
                        <span className="font-semibold text-[#15333A]">
                          {cpl.kode}
                        </span>
                        <span className="font-semibold text-[#15333A] tabular-nums">
                          {formatIndonesianPercent(cpl.capaian)}
                        </span>
                      </div>
                      <p className="text-[12px] text-[#566B70] line-clamp-1">
                        {cpl.label}
                      </p>
                      <div className="h-2 rounded-full bg-[#ECEAE3] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[#15333A]"
                          style={{ width: `${pct ?? 0}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-[#7A8C90]">
                        <span>
                          {cpl.instrumen_lengkap} / {cpl.total_instrumen}{' '}
                          instrumen terisi
                        </span>
                        <span>{cpl.status}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-[18px] font-semibold text-[#15333A]">
                  Mata Kuliah Paket ({selectedPeriod.tahun_akademik}{' '}
                  {selectedPeriod.semester})
                </h2>
                <p className="text-[12.5px] text-[#566B70] mt-0.5">
                  Pilih salah satu mata kuliah untuk meninjau rincian nilai setiap instrumen dan CPMK.
                </p>
              </div>

              <Link
                to="/mahasiswa/mata-kuliah"
                className="text-[12.5px] font-semibold text-[#15333A] hover:text-[#CC6E38] transition-colors"
              >
                Lihat semua →
              </Link>
            </div>

            {classes.length === 0 ? (
              <p className="text-[13px] text-[#566B70]">
                Belum ada paket mata kuliah pada periode ini.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {classes.map((cls) => (
                  <div
                    key={cls.id}
                    className="p-4 rounded-[10px] bg-[#FAF8F3] border border-[#E4DFD4] flex flex-col justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 text-[11.5px] text-[#566B70]">
                        <span className="font-semibold text-[#CC6E38]">
                          {cls.kode_mk}
                        </span>
                        <span>{cls.kelas}</span>
                      </div>
                      <h3 className="text-[15px] font-semibold text-[#15333A] mt-1">
                        {cls.nama_mk}
                      </h3>
                    </div>

                    <Link
                      to={`/mahasiswa/rincian?kelas=${cls.id}`}
                      className="h-8 px-3 rounded-[7px] bg-white border border-[#E4DFD4] hover:border-[#15333A] text-[12px] font-semibold text-[#15333A] inline-flex items-center justify-center transition-colors"
                    >
                      Lihat Rincian Nilai →
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
