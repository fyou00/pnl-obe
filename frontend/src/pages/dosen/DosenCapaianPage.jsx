import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import { getKelasMkCapaian } from '../../lib/adminApi.js';

export default function DosenCapaianPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { classes, selectedPeriod, loadingWorkspace } = useDosenWorkspace();

  const paramClassId = searchParams.get('kelas') || '';
  const activeClassId =
    (paramClassId && classes.some((c) => c.id === paramClassId)
      ? paramClassId
      : classes[0]?.id) || '';

  const [attainment, setAttainment] = useState(null);
  const [chartKind, setChartKind] = useState('CPMK');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Capaian kelas
          </h1>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
            Rekap capaian aktual Sub-CPMK, CPMK, dan CPL dari server backend.
          </p>
        </div>

        <select
          aria-label="Tampilkan mata kuliah"
          value={activeClassId}
          onChange={(e) => setSearchParams({ kelas: e.target.value })}
          disabled={classes.length === 0}
          className="min-w-[260px] h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[12px] font-medium"
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
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#F7EAE1] border border-[#E8B899] px-4 py-3 text-[13px] text-[#9A4213]"
        >
          {error}
        </div>
      )}

      {loadingWorkspace || loading ? (
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 text-[13px] text-[#737373]">
          Memuat data capaian kelas...
        </div>
      ) : !activeClass || !attainment ? (
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 text-[13px] text-[#737373]">
          Belum ada data capaian untuk kelas ini.
        </div>
      ) : (
        <>
          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                  Grafik Radar · {activeClass.nama_mk} ({activeClass.kelas})
                </h2>
                <p className="text-[12px] text-[#737373] dark:text-[#A3A3A0] mt-1">
                  {selectedPeriod
                    ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester}`
                    : ''}
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
              Rekap Agregasi Kelas
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E5E5E5] dark:border-[#2E2E2B] text-[11px] font-medium text-[#737373] dark:text-[#A3A3A0]">
                    <th className="py-3 pr-4">Jenis</th>
                    <th className="py-3 pr-4">Kode</th>
                    <th className="py-3 pr-4">Uraian</th>
                    <th className="py-3 pr-4">Peserta lengkap</th>
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

          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
              Capaian Per Peserta ({attainment.peserta.length})
            </h2>

            {attainment.peserta.length === 0 ? (
              <p className="text-[13px] text-[#737373]">
                Belum ada peserta terdaftar.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#E5E5E5] dark:border-[#2E2E2B] text-[11px] font-medium text-[#737373] dark:text-[#A3A3A0]">
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
                  <tbody className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B] text-[12.5px]">
                    {attainment.peserta.map((student, idx) => {
                      const mkResult = student.hasil.find(
                        (h) => h.jenis === 'Mata kuliah',
                      );
                      return (
                        <tr key={student.mahasiswa_id}>
                          <td className="py-3 pr-4">
                            <span className="font-medium">Peserta #{idx + 1}</span>
                            <div className="text-[11px] font-mono text-[#737373] dark:text-[#A3A3A0]">
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
                                className="py-3 px-2 tabular-nums whitespace-nowrap"
                              >
                                {formatIndonesianPercent(res?.capaian)}
                              </td>
                            );
                          })}
                          <td className="py-3 pl-2 text-right font-semibold tabular-nums whitespace-nowrap">
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
        </>
      )}
    </div>
  );
}
