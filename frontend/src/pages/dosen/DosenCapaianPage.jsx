import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import AnimatedNavIcon from '../../components/icons/AnimatedNavIcon.jsx';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import {
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import { getKelasMkCapaian } from '../../lib/adminApi.js';
import {
  exportCrossClassReport,
  exportKelasMkReport,
  getCrossClassReport,
} from '../../lib/dosenApi.js';

function StatusBadge({ status }) {
  if (status === 'Lengkap') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#E6F2EE] text-[#1A5C4D] text-[11.5px] font-semibold whitespace-nowrap">
        Lengkap
      </span>
    );
  }
  return (
    <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#F7EAE1] text-[#B55824] text-[11.5px] font-semibold whitespace-nowrap">
      {status}
    </span>
  );
}

export default function DosenCapaianPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { classes, selectedPeriodId, selectedPeriod, loadingWorkspace } =
    useDosenWorkspace();

  const paramClassId = searchParams.get('kelas') || '';
  const activeClassId =
    (paramClassId && classes.some((c) => c.id === paramClassId)
      ? paramClassId
      : classes[0]?.id) || '';

  const [attainment, setAttainment] = useState(null);
  const [chartKind, setChartKind] = useState('CPMK');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [exporting, setExporting] = useState('');

  // Lintas kelas
  const [selectedCrossIds, setSelectedCrossIds] = useState([]);
  const [crossReport, setCrossReport] = useState(null);
  const [loadingCross, setLoadingCross] = useState(false);
  const [crossError, setCrossError] = useState('');

  useEffect(() => {
    setSelectedCrossIds((prev) =>
      prev.filter((id) => classes.some((c) => c.id === id)),
    );
    setCrossReport(null);
    setCrossError('');
  }, [classes, selectedPeriodId]);

  const loadData = useCallback(async () => {
    if (!activeClassId) {
      setAttainment(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getKelasMkCapaian(activeClassId);
      setAttainment(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat capaian kelas.');
      setAttainment(null);
    } finally {
      setLoading(false);
    }
  }, [activeClassId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExportClass = async (format) => {
    if (!activeClassId) return;
    setExporting(`class-${format}`);
    setError('');
    setNotice('');
    try {
      const { filename } = await exportKelasMkReport(activeClassId, format);
      setNotice(`Berkas ${filename} berhasil diunduh.`);
    } catch (err) {
      setError(err.message || `Gagal mengekspor laporan kelas (${format}).`);
    } finally {
      setExporting('');
    }
  };

  const toggleCrossClass = (kelasMkId) => {
    setSelectedCrossIds((prev) =>
      prev.includes(kelasMkId)
        ? prev.filter((id) => id !== kelasMkId)
        : [...prev, kelasMkId],
    );
  };

  const handleComputeCrossClass = async () => {
    if (!selectedPeriodId || selectedCrossIds.length < 2) {
      setCrossError('Pilih minimal 2 kelas MK untuk agregasi lintas kelas.');
      return;
    }
    setLoadingCross(true);
    setCrossError('');
    try {
      const data = await getCrossClassReport({
        periode_id: selectedPeriodId,
        kelas_mk_ids: selectedCrossIds,
      });
      setCrossReport(data);
    } catch (err) {
      setCrossError(
        err.message || 'Gagal menghitung agregasi lintas kelas.',
      );
      setCrossReport(null);
    } finally {
      setLoadingCross(false);
    }
  };

  const handleExportCrossClass = async (format) => {
    if (!selectedPeriodId || selectedCrossIds.length < 2) {
      setCrossError('Pilih minimal 2 kelas MK sebelum mengekspor.');
      return;
    }
    setExporting(`cross-${format}`);
    setCrossError('');
    setNotice('');
    try {
      const { filename } = await exportCrossClassReport({
        periode_id: selectedPeriodId,
        kelas_mk_ids: selectedCrossIds,
        format,
      });
      setNotice(`Berkas ${filename} berhasil diunduh.`);
    } catch (err) {
      setCrossError(
        err.message || `Gagal mengekspor laporan lintas kelas (${format}).`,
      );
    } finally {
      setExporting('');
    }
  };

  const activeClass =
    classes.find((c) => c.id === activeClassId) || classes[0] || null;

  const rekap = attainment?.rekap || [];
  const cpmkItems = useMemo(
    () => rekap.filter((r) => r.jenis === 'CPMK'),
    [rekap],
  );
  const cplItems = useMemo(
    () => rekap.filter((r) => r.jenis === 'CPL'),
    [rekap],
  );

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Rekap & Laporan Kelas
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1.5">
            Capaian aktual Sub-CPMK, CPMK, dan CPL per kelas MK dari kalkulasi server serta ekspor CSV/PDF.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <select
            aria-label="Tampilkan mata kuliah"
            value={activeClassId}
            onChange={(e) => setSearchParams({ kelas: e.target.value })}
            disabled={classes.length === 0}
            className="min-w-[240px] h-[38px] px-3 rounded-[8px] bg-white border border-[#E4DFD4] text-[12.5px] font-semibold text-[#15333A] focus:outline-none focus:border-[#15333A]"
          >
            {classes.length === 0 ? (
              <option value="">Belum ada kelas diampu</option>
            ) : (
              classes.map((cls) => (
                <option key={cls.id} value={cls.id}>
                  {cls.nama_mk} · {cls.kelas}
                </option>
              ))
            )}
          </select>

          <button
            type="button"
            disabled={!activeClassId || Boolean(exporting)}
            onClick={() => handleExportClass('csv')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-white border border-[#E4DFD4] hover:border-[#15333A] text-[12.5px] font-semibold text-[#15333A] inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" size={15} />
            <span>{exporting === 'class-csv' ? 'Mengunduh...' : 'Unduh CSV'}</span>
          </button>

          <button
            type="button"
            disabled={!activeClassId || Boolean(exporting)}
            onClick={() => handleExportClass('pdf')}
            className="obe-nav-trigger h-[38px] px-3.5 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-[12.5px] font-semibold text-white inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <AnimatedNavIcon name="download" surface="dark" size={15} />
            <span>{exporting === 'class-pdf' ? 'Mengunduh...' : 'Unduh PDF'}</span>
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

      {loadingWorkspace || loading ? (
        <LoadingSkeleton variant="dashboard" />
      ) : !activeClass || !attainment ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada data capaian untuk kelas ini.
        </div>
      ) : (
        <>
          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-[18px] font-semibold text-[#15333A]">
                  Grafik Radar · {activeClass.nama_mk} ({activeClass.kelas})
                </h2>
                <p className="text-[12.5px] text-[#566B70] mt-1">
                  {selectedPeriod
                    ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester} · Nilai aktual tanpa garis target`
                    : 'Nilai aktual tanpa garis target'}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {['CPMK', 'CPL'].map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => setChartKind(kind)}
                    className={[
                      'h-[32px] px-3.5 rounded-[7px] text-[12px] font-semibold cursor-pointer transition-colors',
                      chartKind === kind
                        ? 'bg-[#15333A] text-white'
                        : 'border border-[#E4DFD4] bg-white text-[#566B70] hover:text-[#15333A]',
                    ].join(' ')}
                  >
                    {kind}
                  </button>
                ))}
              </div>
            </div>

            <RadarCapaianChart
              items={chartKind === 'CPMK' ? cpmkItems : cplItems}
            />

            {cplItems.length > 0 && (
              <div className="border-t border-[#EFECE4] pt-4 flex flex-col gap-3">
                <p className="text-[12.5px] font-semibold text-[#15333A]">
                  Persentase Capaian CPL Aktual (Tanpa Garis Target)
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {cplItems.map((cpl) => {
                    const pct =
                      cpl.capaian !== null && cpl.capaian !== undefined
                        ? Math.min(100, Math.max(0, Number(cpl.capaian)))
                        : null;
                    return (
                      <div
                        key={cpl.id}
                        className="p-3 rounded-[9px] bg-[#FAF8F3] border border-[#EFECE4] flex flex-col gap-1.5"
                      >
                        <div className="flex items-center justify-between text-[12.5px]">
                          <span className="font-semibold text-[#15333A]">
                            {cpl.kode}
                          </span>
                          <span className="font-semibold text-[#15333A] tabular-nums">
                            {formatIndonesianPercent(cpl.capaian)}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-[#ECEAE3] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#15333A]"
                            style={{ width: `${pct ?? 0}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </section>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[18px] font-semibold text-[#15333A]">
              Rekap Agregasi Kelas
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                    <th className="py-3 pr-4">Jenis</th>
                    <th className="py-3 pr-4">Kode</th>
                    <th className="py-3 pr-4">Uraian</th>
                    <th className="py-3 pr-4">Peserta lengkap</th>
                    <th className="py-3 pr-4">Status</th>
                    <th className="py-3 text-right">Capaian aktual</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                  {rekap.map((row) => (
                    <tr key={`${row.jenis}-${row.id}`} className="hover:bg-[#FAF8F3]/70">
                      <td className="py-3 pr-4 text-[#566B70] whitespace-nowrap">
                        {row.jenis}
                      </td>
                      <td className="py-3 pr-4 font-semibold text-[#15333A] whitespace-nowrap">
                        {row.kode}
                      </td>
                      <td className="py-3 pr-4 text-[#334B51] max-w-[420px] truncate">
                        {row.label}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-[#334B51] whitespace-nowrap">
                        {row.mahasiswa_lengkap} / {row.total_mahasiswa}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="py-3 text-right font-semibold tabular-nums text-[#15333A] whitespace-nowrap">
                        {formatIndonesianPercent(row.capaian)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[18px] font-semibold text-[#15333A]">
              Capaian Per Peserta ({attainment.peserta.length})
            </h2>

            {attainment.peserta.length === 0 ? (
              <p className="text-[13px] text-[#566B70]">
                Belum ada peserta terdaftar.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                      <th className="py-3 pr-4 min-w-[240px]">Peserta (UUID)</th>
                      {cpmkItems.map((c) => (
                        <th key={c.id} className="py-3 px-2 whitespace-nowrap">
                          {c.kode}
                        </th>
                      ))}
                      <th className="py-3 pl-2 text-right whitespace-nowrap">
                        Mata kuliah
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EFECE4] text-[12.5px]">
                    {attainment.peserta.map((student, idx) => {
                      const mkResult = student.hasil.find(
                        (h) => h.jenis === 'Mata kuliah',
                      );
                      return (
                        <tr key={student.mahasiswa_id} className="hover:bg-[#FAF8F3]/70">
                          <td className="py-3 pr-4">
                            <span className="font-semibold text-[#15333A]">
                              Peserta #{idx + 1}
                            </span>
                            <div className="text-[11px] font-mono text-[#7A8C90]">
                              {student.mahasiswa_id}
                            </div>
                          </td>
                          {cpmkItems.map((c) => {
                            const res = student.hasil.find(
                              (h) => h.jenis === 'CPMK' && h.id === c.id,
                            );
                            return (
                              <td
                                key={c.id}
                                className="py-3 px-2 tabular-nums text-[#334B51] whitespace-nowrap"
                              >
                                {formatIndonesianPercent(res?.capaian)}
                              </td>
                            );
                          })}
                          <td className="py-3 pl-2 text-right font-semibold tabular-nums text-[#15333A] whitespace-nowrap">
                            {formatIndonesianPercent(mkResult?.capaian)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {classes.length >= 2 && (
            <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#15333A]">
                    Laporan Gabungan Lintas Kelas
                  </h2>
                  <p className="text-[12.5px] text-[#566B70] mt-1">
                    Pilih minimal dua kelas pada versi kurikulum yang sama untuk agregasi rata-rata terbobot mahasiswa lengkap.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={loadingCross || selectedCrossIds.length < 2}
                    onClick={handleComputeCrossClass}
                    className="h-[36px] px-3.5 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold disabled:opacity-50 cursor-pointer"
                  >
                    {loadingCross ? 'Menghitung...' : 'Hitung Lintas Kelas'}
                  </button>
                  <button
                    type="button"
                    disabled={Boolean(exporting) || selectedCrossIds.length < 2}
                    onClick={() => handleExportCrossClass('csv')}
                    className="h-[36px] px-3 rounded-[8px] border border-[#E4DFD4] bg-white hover:border-[#15333A] text-[#15333A] text-[12.5px] font-semibold disabled:opacity-50 cursor-pointer"
                  >
                    {exporting === 'cross-csv' ? 'Mengunduh...' : 'CSV Gabungan'}
                  </button>
                  <button
                    type="button"
                    disabled={Boolean(exporting) || selectedCrossIds.length < 2}
                    onClick={() => handleExportCrossClass('pdf')}
                    className="h-[36px] px-3 rounded-[8px] border border-[#E4DFD4] bg-white hover:border-[#15333A] text-[#15333A] text-[12.5px] font-semibold disabled:opacity-50 cursor-pointer"
                  >
                    {exporting === 'cross-pdf' ? 'Mengunduh...' : 'PDF Gabungan'}
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2.5">
                {classes.map((cls) => {
                  const checked = selectedCrossIds.includes(cls.id);
                  return (
                    <label
                      key={cls.id}
                      className={[
                        'inline-flex items-center gap-2 px-3 py-2 rounded-[8px] border text-[12.5px] cursor-pointer transition-colors',
                        checked
                          ? 'bg-[#E6F0EE] border-[#15333A] text-[#15333A] font-semibold'
                          : 'bg-[#FAF8F3] border-[#E4DFD4] text-[#334B51]',
                      ].join(' ')}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleCrossClass(cls.id)}
                        className="accent-[#15333A]"
                      />
                      <span>
                        {cls.kode_mk} · {cls.nama_mk} ({cls.kelas})
                      </span>
                    </label>
                  );
                })}
              </div>

              {crossError && (
                <div
                  role="alert"
                  className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
                >
                  {crossError}
                </div>
              )}

              {crossReport && (
                <div className="border-t border-[#EFECE4] pt-4 flex flex-col gap-3">
                  <p className="text-[12.5px] font-medium text-[#566B70]">
                    Kurikulum {crossReport.kode_kurikulum} · Kelas tergabung:{' '}
                    <strong className="text-[#15333A]">
                      {crossReport.kelas_labels.join(', ')}
                    </strong>
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                          <th className="py-2.5 pr-4">Jenis</th>
                          <th className="py-2.5 pr-4">Kode</th>
                          <th className="py-2.5 pr-4">Uraian</th>
                          <th className="py-2.5 pr-4">Lengkap</th>
                          <th className="py-2.5 pr-4">Status</th>
                          <th className="py-2.5 text-right">Capaian Gabungan</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#EFECE4] text-[12.5px]">
                        {crossReport.rekap.map((row) => (
                          <tr key={`${row.jenis}-${row.id}`}>
                            <td className="py-2.5 pr-4 text-[#566B70]">
                              {row.jenis}
                            </td>
                            <td className="py-2.5 pr-4 font-semibold text-[#15333A]">
                              {row.kode}
                            </td>
                            <td className="py-2.5 pr-4 text-[#334B51]">
                              {row.label}
                            </td>
                            <td className="py-2.5 pr-4 tabular-nums">
                              {row.mahasiswa_lengkap} / {row.total_mahasiswa}
                            </td>
                            <td className="py-2.5 pr-4">
                              <StatusBadge status={row.status} />
                            </td>
                            <td className="py-2.5 text-right font-semibold tabular-nums text-[#15333A]">
                              {formatIndonesianPercent(row.capaian)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
