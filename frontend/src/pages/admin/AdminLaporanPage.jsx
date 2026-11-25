import { useCallback, useEffect, useMemo, useState } from 'react';
import AnimatedNavIcon from '../../components/icons/AnimatedNavIcon.jsx';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import {
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  exportKelasMkReport,
  exportProdiReport,
  getProdiReport,
  listAuditLogs,
} from '../../lib/adminApi.js';

const AUDIT_ACTION_OPTIONS = [
  { value: '', label: 'Semua aksi' },
  { value: 'create', label: 'Tambah (create)' },
  { value: 'update', label: 'Ubah (update)' },
  { value: 'delete', label: 'Hapus (delete)' },
  { value: 'close', label: 'Tutup periode (close)' },
  { value: 'reopen', label: 'Buka kembali (reopen)' },
  { value: 'apply_paket', label: 'Terapkan paket (apply_paket)' },
  { value: 'copy', label: 'Salin rancangan (copy)' },
];

function formatAuditTime(isoString) {
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const formatted = new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
  return `${formatted} WIB`;
}

function StatusBadge({ status }) {
  if (status === 'Lengkap') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#E6F2EE] text-[#1A5C4D] text-[11.5px] font-semibold whitespace-nowrap">
        Lengkap
      </span>
    );
  }
  if (status === 'Belum siap dinilai') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#FEF3F2] text-[#B42318] text-[11.5px] font-semibold whitespace-nowrap">
        Belum siap dinilai
      </span>
    );
  }
  return (
    <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#F7EAE1] text-[#B55824] text-[11.5px] font-semibold whitespace-nowrap">
      {status || 'Belum lengkap'}
    </span>
  );
}

export default function AdminLaporanPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedPeriodId,
    selectedPeriod,
    loadingMeta,
  } = useAdminWorkspace();

  const [activeTab, setActiveTab] = useState('rekap');
  const [semesterFilter, setSemesterFilter] = useState('');
  const [report, setReport] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [aksiFilter, setAksiFilter] = useState('');
  const [auditQuery, setAuditQuery] = useState('');
  const [submittedAuditQuery, setSubmittedAuditQuery] = useState('');

  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [exportingKey, setExportingKey] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadReport = useCallback(async () => {
    if (!selectedPeriodId || !selectedCurriculumId) {
      setReport(null);
      return;
    }
    setLoadingReport(true);
    setError('');
    try {
      const data = await getProdiReport({
        periode_id: selectedPeriodId,
        kurikulum_id: selectedCurriculumId,
        semester: semesterFilter ? Number(semesterFilter) : undefined,
      });
      setReport(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat laporan capaian program studi.');
      setReport(null);
    } finally {
      setLoadingReport(false);
    }
  }, [selectedCurriculumId, selectedPeriodId, semesterFilter]);

  const loadAudit = useCallback(async () => {
    if (!selectedPeriodId) {
      setAuditLogs([]);
      return;
    }
    setLoadingAudit(true);
    setError('');
    try {
      const data = await listAuditLogs({
        periode_id: selectedPeriodId,
        aksi: aksiFilter || undefined,
        q: submittedAuditQuery || undefined,
        limit: 100,
      });
      setAuditLogs(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat jejak audit.');
    } finally {
      setLoadingAudit(false);
    }
  }, [aksiFilter, selectedPeriodId, submittedAuditQuery]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  useEffect(() => {
    loadAudit();
  }, [loadAudit]);

  const handleExportProdi = async (format) => {
    if (!selectedPeriodId || !selectedCurriculumId) return;
    setExportingKey(`prodi-${format}`);
    setError('');
    setNotice('');
    try {
      const { filename } = await exportProdiReport({
        periode_id: selectedPeriodId,
        kurikulum_id: selectedCurriculumId,
        semester: semesterFilter ? Number(semesterFilter) : undefined,
        format,
      });
      setNotice(`Berkas ${filename} berhasil diunduh.`);
    } catch (err) {
      setError(err.message || `Gagal mengekspor laporan prodi (${format}).`);
    } finally {
      setExportingKey('');
    }
  };

  const handleExportClass = async (kelasMkId, format) => {
    setExportingKey(`${kelasMkId}-${format}`);
    setError('');
    setNotice('');
    try {
      const { filename } = await exportKelasMkReport(kelasMkId, format);
      setNotice(`Berkas ${filename} berhasil diunduh.`);
    } catch (err) {
      setError(err.message || `Gagal mengekspor laporan kelas (${format}).`);
    } finally {
      setExportingKey('');
    }
  };

  const rekapCpl = report?.rekap_cpl || [];
  const completeCplCount = useMemo(
    () => rekapCpl.filter((item) => item.status === 'Lengkap').length,
    [rekapCpl],
  );

  const isBusy = loadingMeta || loadingReport;

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Laporan & Audit Log
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1.5">
            Rekap agregasi CPL prodi terisolasi per versi kurikulum, unduhan CSV/PDF resmi, dan riwayat audit periode.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <select
            aria-label="Pilih versi kurikulum"
            value={selectedCurriculumId}
            onChange={(e) => setSelectedCurriculumId(e.target.value)}
            disabled={curricula.length === 0}
            className="h-[38px] min-w-[200px] px-3 rounded-[8px] bg-white border border-[#E4DFD4] text-[12.5px] font-semibold text-[#15333A] focus:outline-none focus:border-[#15333A]"
          >
            {curricula.length === 0 ? (
              <option value="">Belum ada kurikulum</option>
            ) : (
              curricula.map((kur) => (
                <option key={kur.id} value={kur.id}>
                  {kur.kode_kurikulum} ({kur.status})
                </option>
              ))
            )}
          </select>

          <select
            aria-label="Filter semester"
            value={semesterFilter}
            onChange={(e) => setSemesterFilter(e.target.value)}
            className="h-[38px] px-3 rounded-[8px] bg-white border border-[#E4DFD4] text-[12.5px] font-semibold text-[#15333A] focus:outline-none focus:border-[#15333A]"
          >
            <option value="">Semua Semester (1–8)</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
              <option key={sem} value={String(sem)}>
                Semester {sem}
              </option>
            ))}
          </select>

          <button
            type="button"
            disabled={!selectedPeriodId || !selectedCurriculumId || Boolean(exportingKey)}
            onClick={() => handleExportProdi('csv')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-white border border-[#E4DFD4] hover:border-[#15333A] text-[12.5px] font-semibold text-[#15333A] inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" size={15} />
            <span>{exportingKey === 'prodi-csv' ? 'Mengunduh...' : 'Unduh CSV Prodi'}</span>
          </button>

          <button
            type="button"
            disabled={!selectedPeriodId || !selectedCurriculumId || Boolean(exportingKey)}
            onClick={() => handleExportProdi('pdf')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-[12.5px] font-semibold text-white inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" surface="dark" size={15} />
            <span>{exportingKey === 'prodi-pdf' ? 'Mengunduh...' : 'Unduh PDF Prodi'}</span>
          </button>
        </div>
      </div>

      <LockedPeriodBanner period={selectedPeriod} />

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

      {!selectedPeriod || !selectedCurriculumId ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Pilih periode akademik di topbar dan versi kurikulum terlebih dahulu.
        </div>
      ) : isBusy ? (
        <LoadingSkeleton variant="dashboard" />
      ) : (
        <>
          <div className="rounded-[10px] bg-[#EBF3F7] border border-[#C7DCE8] px-4 py-3 flex flex-wrap items-center justify-between gap-2 text-[12.5px] text-[#1E4D6B]">
            <span>
              <strong>Isolasi Kurikulum:</strong> Data di bawah hanya
              mencakup{' '}
              <strong>
                {report
                  ? `${report.kode_kurikulum} (${report.nama_kurikulum})`
                  : selectedCurriculumId}
              </strong>{' '}
              pada periode {selectedPeriod.tahun_akademik}{' '}
              {selectedPeriod.semester}. Kelas khusus TI-K dikecualikan otomatis
              dan nilai kosong tidak pernah diganti menjadi 0.
            </span>
          </div>

          {report && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="min-h-[116px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
                <span className="text-[12.5px] font-medium text-[#566B70]">
                  Total Kelas MK
                </span>
                <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                  {report.total_kelas_mk}
                </span>
                <span className="text-[11px] text-[#7A8C90]">
                  {semesterFilter
                    ? `Filter Semester ${semesterFilter}`
                    : 'Semua semester paket'}
                </span>
              </div>

              <div className="min-h-[116px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
                <span className="text-[12.5px] font-medium text-[#566B70]">
                  Peserta Lengkap
                </span>
                <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                  {report.total_peserta_lengkap} / {report.total_peserta}
                </span>
                <span className="text-[11px] text-[#7A8C90]">
                  Akumulasi kursi peserta kelas MK
                </span>
              </div>

              <div className="min-h-[116px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
                <span className="text-[12.5px] font-medium text-[#566B70]">
                  CPL Lengkap Terukur
                </span>
                <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                  {completeCplCount} / {rekapCpl.length}
                </span>
                <span className="text-[11px] text-[#7A8C90]">
                  {report.kode_kurikulum} (tanpa garis target)
                </span>
              </div>

              <div className="min-h-[116px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
                <span className="text-[12.5px] font-medium text-[#566B70]">
                  Jejak Audit Periode
                </span>
                <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
                  {report.total_audit_periode}
                </span>
                <span className="text-[11px] text-[#7A8C90]">
                  Tercatat untuk {selectedPeriod.tahun_akademik}{' '}
                  {selectedPeriod.semester}
                </span>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 border-b border-[#E4DFD4] pb-3">
            <button
              type="button"
              onClick={() => setActiveTab('rekap')}
              className={[
                'h-[36px] px-4 rounded-[8px] text-[13px] font-semibold cursor-pointer transition-colors',
                activeTab === 'rekap'
                  ? 'bg-[#15333A] text-white'
                  : 'bg-white border border-[#E4DFD4] text-[#566B70] hover:text-[#15333A]',
              ].join(' ')}
            >
              Rekap Prodi & CPL
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('audit')}
              className={[
                'h-[36px] px-4 rounded-[8px] text-[13px] font-semibold inline-flex items-center gap-2 cursor-pointer transition-colors',
                activeTab === 'audit'
                  ? 'bg-[#15333A] text-white'
                  : 'bg-white border border-[#E4DFD4] text-[#566B70] hover:text-[#15333A]',
              ].join(' ')}
            >
              <AnimatedNavIcon
                name="audit"
                active={activeTab === 'audit'}
                surface={activeTab === 'audit' ? 'dark' : 'light'}
                size={15}
              />
              <span>Jejak Audit Log ({auditLogs.length})</span>
            </button>
          </div>

          {activeTab === 'rekap' ? (
            !report ? (
              <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
                Data laporan prodi tidak tersedia.
              </div>
            ) : (
              <>
                <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
                  <div>
                    <h2 className="text-[18px] font-semibold text-[#15333A]">
                      Agregasi Capaian CPL Program Studi · {report.kode_kurikulum}
                    </h2>
                    <p className="text-[12.5px] text-[#566B70] mt-1">
                      Rata-rata terbobot dari seluruh mahasiswa lengkap tanpa garis target atau substitusi nol.
                    </p>
                  </div>

                  <RadarCapaianChart
                    items={rekapCpl}
                    emptyMessage="Belum ada CPL yang terpetakan pada kelas periode ini."
                  />

                  {rekapCpl.length > 0 && (
                    <div className="border-t border-[#EFECE4] pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      {rekapCpl.map((cpl) => {
                        const pct =
                          cpl.capaian !== null && cpl.capaian !== undefined
                            ? Math.min(100, Math.max(0, Number(cpl.capaian)))
                            : null;
                        return (
                          <div
                            key={cpl.id}
                            className="p-3.5 rounded-[10px] bg-[#FAF8F3] border border-[#EFECE4] flex flex-col gap-2"
                          >
                            <div className="flex items-center justify-between gap-3 text-[12.5px]">
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
                                className="h-full rounded-full bg-[#15333A] transition-all"
                                style={{ width: `${pct ?? 0}%` }}
                              />
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-[#7A8C90]">
                              <span>
                                {cpl.mahasiswa_lengkap} / {cpl.total_mahasiswa}{' '}
                                lengkap
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
                    <h2 className="text-[18px] font-semibold text-[#15333A]">
                      Rekap Pelaksanaan & Capaian Kelas MK ({report.kelas.length})
                    </h2>
                  </div>

                  {report.kelas.length === 0 ? (
                    <p className="text-[13px] text-[#566B70]">
                      Belum ada kelas MK untuk kombinasi periode, kurikulum, dan semester terpilih.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                            <th className="py-3 pr-4">Kelas</th>
                            <th className="py-3 pr-4">Mata Kuliah</th>
                            <th className="py-3 pr-4">Sem / SKS</th>
                            <th className="py-3 pr-4">Dosen Pengampu</th>
                            <th className="py-3 pr-4">Bobot</th>
                            <th className="py-3 pr-4">Kelengkapan</th>
                            <th className="py-3 pr-4">Status</th>
                            <th className="py-3 pr-4 text-right">Capaian MK</th>
                            <th className="py-3 text-right">Ekspor</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                          {report.kelas.map((cls) => (
                            <tr key={cls.kelas_mk_id} className="hover:bg-[#FAF8F3]/70">
                              <td className="py-3 pr-4 font-semibold text-[#15333A] whitespace-nowrap">
                                {cls.kelas}
                              </td>
                              <td className="py-3 pr-4 min-w-[200px]">
                                <span className="font-semibold text-[#15333A]">
                                  {cls.kode_mk}
                                </span>
                                <span className="text-[#566B70]">
                                  {' '}
                                  · {cls.nama_mk}
                                </span>
                              </td>
                              <td className="py-3 pr-4 text-[#566B70] tabular-nums whitespace-nowrap">
                                Sem {cls.semester} · {cls.sks} SKS
                              </td>
                              <td className="py-3 pr-4 text-[#334B51] whitespace-nowrap">
                                {cls.dosen_nama}
                              </td>
                              <td className="py-3 pr-4 tabular-nums text-[#334B51] whitespace-nowrap">
                                {formatIndonesianPercent(cls.total_bobot)}
                              </td>
                              <td className="py-3 pr-4 tabular-nums text-[#334B51] whitespace-nowrap">
                                {cls.mahasiswa_lengkap} / {cls.total_mahasiswa}
                              </td>
                              <td className="py-3 pr-4 whitespace-nowrap">
                                <StatusBadge status={cls.status} />
                              </td>
                              <td className="py-3 pr-4 text-right font-semibold tabular-nums text-[#15333A] whitespace-nowrap">
                                {formatIndonesianPercent(cls.capaian_mk)}
                              </td>
                              <td className="py-3 text-right whitespace-nowrap">
                                <div className="inline-flex items-center gap-1.5">
                                  <button
                                    type="button"
                                    disabled={Boolean(exportingKey)}
                                    onClick={() =>
                                      handleExportClass(cls.kelas_mk_id, 'csv')
                                    }
                                    className="h-7 px-2.5 rounded-[6px] border border-[#E4DFD4] bg-white hover:border-[#15333A] text-[11.5px] font-semibold text-[#15333A] disabled:opacity-50 cursor-pointer"
                                  >
                                    CSV
                                  </button>
                                  <button
                                    type="button"
                                    disabled={Boolean(exportingKey)}
                                    onClick={() =>
                                      handleExportClass(cls.kelas_mk_id, 'pdf')
                                    }
                                    className="h-7 px-2.5 rounded-[6px] bg-[#15333A] hover:bg-[#193A40] text-[11.5px] font-semibold text-white disabled:opacity-50 cursor-pointer"
                                  >
                                    PDF
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              </>
            )
          ) : (
            <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#15333A]">
                    Riwayat Jejak Audit ({selectedPeriod.tahun_akademik}{' '}
                    {selectedPeriod.semester})
                  </h2>
                  <p className="text-[12.5px] text-[#566B70] mt-0.5">
                    Mencatat mutasi nilai, penutupan, serta alasan pembukaan kembali periode tanpa menampilkan field sensitif.
                  </p>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setSubmittedAuditQuery(auditQuery.trim());
                  }}
                  className="flex flex-wrap items-center gap-2"
                >
                  <select
                    aria-label="Filter aksi audit"
                    value={aksiFilter}
                    onChange={(e) => setAksiFilter(e.target.value)}
                    className="h-[36px] px-3 rounded-[8px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px] font-medium text-[#15333A]"
                  >
                    {AUDIT_ACTION_OPTIONS.map((opt) => (
                      <option key={opt.value || 'all'} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>

                  <input
                    type="search"
                    value={auditQuery}
                    onChange={(e) => setAuditQuery(e.target.value)}
                    placeholder="Cari aktor, entitas, atau alasan..."
                    className="h-[36px] w-[220px] px-3 rounded-[8px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px] text-[#15333A] placeholder:text-[#7A8C90] focus:outline-none focus:border-[#15333A] focus:bg-white"
                  />

                  <button
                    type="submit"
                    className="h-[36px] px-3.5 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold cursor-pointer"
                  >
                    Filter
                  </button>
                </form>
              </div>

              {loadingAudit ? (
                <LoadingSkeleton variant="table" />
              ) : auditLogs.length === 0 ? (
                <div className="py-8 text-center text-[13px] text-[#566B70] bg-[#FAF8F3] rounded-[10px] border border-[#EFECE4]">
                  Belum ada catatan audit yang sesuai filter periode ini.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                        <th className="py-3 pr-4">Waktu (WIB)</th>
                        <th className="py-3 pr-4">Aktor</th>
                        <th className="py-3 pr-4">Aksi</th>
                        <th className="py-3 pr-4">Entitas</th>
                        <th className="py-3">Alasan / Catatan</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EFECE4] text-[12.5px]">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-[#FAF8F3]/70">
                          <td className="py-3 pr-4 tabular-nums text-[#566B70] whitespace-nowrap">
                            {formatAuditTime(log.waktu)}
                          </td>
                          <td className="py-3 pr-4 whitespace-nowrap">
                            <span className="font-semibold text-[#15333A]">
                              {log.aktor_nama}
                            </span>
                            <span className="ml-1.5 inline-flex items-center px-2 py-0.5 rounded-full bg-[#E6F0EE] text-[#15333A] text-[10.5px] font-semibold">
                              {log.aktor_role}
                            </span>
                          </td>
                          <td className="py-3 pr-4 whitespace-nowrap">
                            <span
                              className={[
                                'inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold',
                                log.aksi === 'reopen' || log.aksi === 'close'
                                  ? 'bg-[#F7EAE1] text-[#B55824]'
                                  : 'bg-[#F3EFE6] text-[#15333A]',
                              ].join(' ')}
                            >
                              {log.aksi}
                            </span>
                          </td>
                          <td className="py-3 pr-4 font-mono text-[12px] text-[#334B51] whitespace-nowrap">
                            {log.entitas}
                          </td>
                          <td className="py-3 text-[#334B51] max-w-[360px]">
                            {log.alasan ? (
                              <span className="text-[#9A4213] font-medium">
                                {log.alasan}
                              </span>
                            ) : (
                              <span className="text-[#7A8C90]">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
