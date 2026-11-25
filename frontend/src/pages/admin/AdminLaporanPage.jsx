import { useCallback, useEffect, useMemo, useState } from 'react';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import { getKelasMkCapaian, listKelasMk } from '../../lib/adminApi.js';

export default function AdminLaporanPage() {
  const { selectedPeriodId, selectedPeriod } = useAdminWorkspace();

  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [attainment, setAttainment] = useState(null);
  const [chartKind, setChartKind] = useState('CPMK');

  const [loadingClasses, setLoadingClasses] = useState(false);
  const [loadingAttainment, setLoadingAttainment] = useState(false);
  const [error, setError] = useState('');

  const loadClasses = useCallback(async () => {
    if (!selectedPeriodId) {
      setClasses([]);
      setSelectedClassId('');
      return;
    }
    setLoadingClasses(true);
    setError('');
    try {
      const data = await listKelasMk(selectedPeriodId, { limit: 100 });
      setClasses(data);
      setSelectedClassId((prev) =>
        prev && data.some((c) => c.id === prev) ? prev : data[0]?.id || '',
      );
    } catch (err) {
      setError(err.message || 'Gagal memuat daftar kelas mata kuliah.');
    } finally {
      setLoadingClasses(false);
    }
  }, [selectedPeriodId]);

  useEffect(() => {
    loadClasses();
  }, [loadClasses]);

  const loadAttainment = useCallback(async () => {
    if (!selectedClassId) {
      setAttainment(null);
      return;
    }
    setLoadingAttainment(true);
    setError('');
    try {
      const data = await getKelasMkCapaian(selectedClassId);
      setAttainment(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat rekap capaian kelas.');
      setAttainment(null);
    } finally {
      setLoadingAttainment(false);
    }
  }, [selectedClassId]);

  useEffect(() => {
    loadAttainment();
  }, [loadAttainment]);

  const selectedClass = classes.find((c) => c.id === selectedClassId) || null;
  const rekap = attainment?.rekap || [];

  const mkSummary = useMemo(
    () => rekap.find((item) => item.jenis === 'Mata kuliah') || null,
    [rekap],
  );
  const cpmkItems = useMemo(
    () => rekap.filter((item) => item.jenis === 'CPMK'),
    [rekap],
  );
  const cplItems = useMemo(
    () => rekap.filter((item) => item.jenis === 'CPL'),
    [rekap],
  );

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Laporan OBE
          </h1>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
            Rekap capaian aktual kelas mata kuliah dari layanan kalkulasi backend.
          </p>
        </div>

        <select
          aria-label="Pilih kelas mata kuliah"
          value={selectedClassId}
          onChange={(e) => setSelectedClassId(e.target.value)}
          disabled={classes.length === 0 || loadingClasses}
          className="min-w-[260px] h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[12px] font-medium"
        >
          {classes.length === 0 ? (
            <option value="">Belum ada kelas MK pada periode ini</option>
          ) : (
            classes.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.nama_mk} · {cls.kelas}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="rounded-[10px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] px-4 py-3 flex items-center justify-between gap-4 text-[12.5px] text-[#525252] dark:text-[#D4D4D0]">
        <span>
          Rekap capaian tampil langsung dari server (tanpa asumsi nol dan tanpa
          target buatan). Fitur unduh berkas ekspor CSV/PDF resmi masih
          menunggu endpoint ekspor backend.
        </span>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#F7EAE1] border border-[#E8B899] px-4 py-3 text-[13px] text-[#9A4213]"
        >
          {error}
        </div>
      )}

      {!selectedPeriod ? (
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 text-[13px] text-[#737373]">
          Pilih periode akademik di topbar terlebih dahulu.
        </div>
      ) : loadingClasses || loadingAttainment ? (
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 text-[13px] text-[#737373]">
          Memuat rekap capaian kelas...
        </div>
      ) : !selectedClass || !attainment ? (
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 text-[13px] text-[#737373]">
          Belum ada data capaian kelas MK pada periode{' '}
          {selectedPeriod.tahun_akademik} {selectedPeriod.semester}.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-6">
            <div className="min-h-[120px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
              <span className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                Peserta lengkap
              </span>
              <span className="text-[28px] font-semibold tabular-nums">
                {mkSummary
                  ? `${mkSummary.mahasiswa_lengkap} / ${mkSummary.total_mahasiswa}`
                  : `0 / ${attainment.peserta.length}`}
              </span>
              <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                {selectedClass.kelas} · {selectedClass.kode_mk}
              </span>
            </div>

            <div className="min-h-[120px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
              <span className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                Capaian Mata Kuliah
              </span>
              <span className="text-[28px] font-semibold tabular-nums">
                {formatIndonesianPercent(mkSummary?.capaian)}
              </span>
              <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                {mkSummary?.status || '—'}
              </span>
            </div>

            <div className="min-h-[120px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
              <span className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                CPMK Lengkap
              </span>
              <span className="text-[28px] font-semibold tabular-nums">
                {cpmkItems.filter((i) => i.status === 'Lengkap').length} /{' '}
                {cpmkItems.length}
              </span>
              <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                Berdasarkan seluruh peserta
              </span>
            </div>

            <div className="min-h-[120px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
              <span className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                CPL Lengkap
              </span>
              <span className="text-[28px] font-semibold tabular-nums">
                {cplItems.filter((i) => i.status === 'Lengkap').length} /{' '}
                {cplItems.length}
              </span>
              <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                Dalam kurikulum MK terkait
              </span>
            </div>
          </div>

          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                  Visualisasi Radar Capaian · {selectedClass.nama_mk} (
                  {selectedClass.kelas})
                </h2>
                <p className="text-[12px] text-[#737373] dark:text-[#A3A3A0] mt-1">
                  {selectedPeriod.tahun_akademik} {selectedPeriod.semester}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {['CPMK', 'CPL'].map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => setChartKind(kind)}
                    className={[
                      'h-[32px] px-3 rounded-[7px] text-[12px] font-medium cursor-pointer',
                      chartKind === kind
                        ? 'bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525]'
                        : 'border border-[#E5E5E5] dark:border-[#343430] text-[#525252] dark:text-[#A3A3A0]',
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
          </section>

          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
              Rincian Rekap Capaian Kelas
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E5E5E5] dark:border-[#2E2E2B] text-[11px] font-medium text-[#737373] dark:text-[#A3A3A0]">
                    <th className="py-3 pr-4">Jenis</th>
                    <th className="py-3 pr-4">Kode</th>
                    <th className="py-3 pr-4">Uraian</th>
                    <th className="py-3 pr-4">Kelengkapan</th>
                    <th className="py-3 pr-4">Status</th>
                    <th className="py-3 text-right">Capaian aktual</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B] text-[13px]">
                  {rekap.map((row) => (
                    <tr key={`${row.jenis}-${row.id}`}>
                      <td className="py-3 pr-4 text-[#737373] dark:text-[#A3A3A0] whitespace-nowrap">
                        {row.jenis}
                      </td>
                      <td className="py-3 pr-4 font-semibold whitespace-nowrap">
                        {row.kode}
                      </td>
                      <td className="py-3 pr-4 max-w-[420px] truncate">
                        {row.label}
                      </td>
                      <td className="py-3 pr-4 tabular-nums whitespace-nowrap">
                        {row.mahasiswa_lengkap} / {row.total_mahasiswa}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        <span
                          className={
                            row.status === 'Lengkap'
                              ? 'text-[#1A5C4D] dark:text-[#86EFAC]'
                              : 'text-[#B55824] dark:text-[#F0C3A4]'
                          }
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="py-3 text-right font-semibold tabular-nums whitespace-nowrap">
                        {formatIndonesianPercent(row.capaian)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
