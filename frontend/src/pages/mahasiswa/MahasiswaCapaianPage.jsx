import { useCallback, useEffect, useState } from 'react';
import AnimatedNavIcon from '../../components/icons/AnimatedNavIcon.jsx';
import RadarCapaianChart, {
  formatIndonesianPercent,
} from '../../components/dashboard/RadarCapaianChart.jsx';
import {
  EmptyTikState,
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';
import {
  exportMahasiswaCapaianSaya,
  getMahasiswaCapaianSaya,
} from '../../lib/mahasiswaApi.js';

export default function MahasiswaCapaianPage() {
  const {
    periods,
    selectedPeriodId,
    selectedPeriod,
    isTikOrInactive,
    loadingWorkspace,
  } = useMahasiswaWorkspace();

  const [kumulatif, setKumulatif] = useState(false);
  const [attainment, setAttainment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadData = useCallback(async () => {
    if (!selectedPeriodId) {
      setAttainment(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getMahasiswaCapaianSaya(selectedPeriodId, {
        kumulatif,
      });
      setAttainment(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat capaian CPL pribadi.');
      setAttainment(null);
    } finally {
      setLoading(false);
    }
  }, [kumulatif, selectedPeriodId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
      setError(err.message || `Gagal mengunduh berkas capaian (${format}).`);
    } finally {
      setExporting('');
    }
  };

  const results = attainment?.hasil || [];

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Capaian CPL Pribadi
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1.5">
            Agregasi capaian CPL per periode maupun kumulatif pada kurikulum angkatan Anda (tanpa garis target dan tanpa nilai rata-rata kelas).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => setKumulatif(false)}
            className={[
              'h-[36px] px-3 rounded-[8px] text-[12.5px] font-semibold cursor-pointer transition-colors',
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
              'h-[36px] px-3 rounded-[8px] text-[12.5px] font-semibold cursor-pointer transition-colors',
              kumulatif
                ? 'bg-[#15333A] text-white'
                : 'border border-[#E4DFD4] bg-white text-[#566B70] hover:text-[#15333A]',
            ].join(' ')}
          >
            Kumulatif
          </button>

          <button
            type="button"
            disabled={!selectedPeriodId || Boolean(exporting)}
            onClick={() => handleExport('csv')}
            className="obe-nav-trigger h-[36px] px-3 rounded-[8px] bg-white border border-[#E4DFD4] hover:border-[#15333A] text-[12.5px] font-semibold text-[#15333A] inline-flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            <AnimatedNavIcon name="download" size={14} />
            <span>{exporting === 'csv' ? 'Mengunduh...' : 'CSV'}</span>
          </button>
          <button
            type="button"
            disabled={!selectedPeriodId || Boolean(exporting)}
            onClick={() => handleExport('pdf')}
            className="obe-nav-trigger h-[36px] px-3 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-[12.5px] font-semibold text-white inline-flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
          >
            <AnimatedNavIcon name="download" surface="dark" size={14} />
            <span>{exporting === 'pdf' ? 'Mengunduh...' : 'PDF'}</span>
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
      ) : !selectedPeriod ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada data periode akademik.
        </div>
      ) : isTikOrInactive && !kumulatif ? (
        <div className="flex flex-col gap-4">
          <EmptyTikState
            period={selectedPeriod}
            classLabel={selectedPeriod.kelas}
            studentStatus={selectedPeriod.status_mahasiswa}
            hasOtherPeriods={periods.length > 1}
          />
          {periods.length > 1 && (
            <button
              type="button"
              onClick={() => setKumulatif(true)}
              className="self-start h-9 px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[13px] font-semibold cursor-pointer"
            >
              Tampilkan Riwayat CPL Kumulatif →
            </button>
          )}
        </div>
      ) : (
        <>
          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <div>
              <h2 className="text-[18px] font-semibold text-[#15333A]">
                Visualisasi Radar CPL · {selectedPeriod.kode_kurikulum}
              </h2>
              <p className="text-[12.5px] text-[#566B70] mt-0.5">
                {kumulatif
                  ? `Cakupan kumulatif hingga ${selectedPeriod.tahun_akademik} ${selectedPeriod.semester} (${attainment?.kelas_mk_ids?.length ?? 0} kelas MK)`
                  : `Periode ${selectedPeriod.tahun_akademik} ${selectedPeriod.semester} (${attainment?.kelas_mk_ids?.length ?? 0} kelas MK)`}
              </p>
            </div>

            <RadarCapaianChart
              items={results}
              emptyMessage="Belum ada CPL yang dapat dihitung pada cakupan ini."
            />
          </section>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[18px] font-semibold text-[#15333A]">
              Tabel Rincian Capaian CPL ({results.length})
            </h2>

            {results.length === 0 ? (
              <p className="text-[13px] text-[#566B70]">
                Belum ada instrumen CPL yang terdata pada periode ini.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                      <th className="py-3 pr-4">Kode CPL</th>
                      <th className="py-3 pr-4">Deskripsi CPL</th>
                      <th className="py-3 pr-4">Kelengkapan Instrumen</th>
                      <th className="py-3 pr-4">Status</th>
                      <th className="py-3 text-right">Capaian Aktual</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                    {results.map((item) => (
                      <tr key={item.id} className="hover:bg-[#FAF8F3]/70">
                        <td className="py-3 pr-4 font-semibold text-[#15333A] whitespace-nowrap">
                          {item.kode}
                        </td>
                        <td className="py-3 pr-4 text-[#334B51]">
                          {item.label}
                        </td>
                        <td className="py-3 pr-4 tabular-nums text-[#334B51] whitespace-nowrap">
                          {item.instrumen_lengkap} / {item.total_instrumen}
                        </td>
                        <td className="py-3 pr-4 whitespace-nowrap">
                          <span
                            className={[
                              'inline-flex items-center h-6 px-2.5 rounded-full text-[11.5px] font-semibold',
                              item.status === 'Lengkap'
                                ? 'bg-[#E6F2EE] text-[#1A5C4D]'
                                : 'bg-[#F7EAE1] text-[#B55824]',
                            ].join(' ')}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="py-3 text-right font-semibold tabular-nums text-[#15333A] whitespace-nowrap">
                          {formatIndonesianPercent(item.capaian)}
                        </td>
                      </tr>
                    ))}
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
