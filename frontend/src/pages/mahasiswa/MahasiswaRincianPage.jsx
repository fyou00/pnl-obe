import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { formatIndonesianPercent } from '../../components/dashboard/RadarCapaianChart.jsx';
import {
  EmptyTikState,
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';
import { getMahasiswaKelasRincian } from '../../lib/mahasiswaApi.js';

function formatIndonesianScore(value) {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return '—';
  return num.toFixed(2).replace('.', ',');
}

export default function MahasiswaRincianPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    periods,
    selectedPeriod,
    isTikOrInactive,
    classes,
    loadingWorkspace,
  } = useMahasiswaWorkspace();

  const paramClassId = searchParams.get('kelas') || '';
  const activeClassId =
    (paramClassId && classes.some((c) => c.id === paramClassId)
      ? paramClassId
      : classes[0]?.id) || '';

  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState('');

  const loadCourseDetail = useCallback(async () => {
    if (!activeClassId || isTikOrInactive) {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    setError('');
    try {
      const data = await getMahasiswaKelasRincian(activeClassId);
      setDetail(data);
    } catch (err) {
      setError(
        err.message || 'Gagal memuat rincian nilai dan capaian mata kuliah.',
      );
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }, [activeClassId, isTikOrInactive]);

  useEffect(() => {
    loadCourseDetail();
  }, [loadCourseDetail]);

  const hasil = detail?.hasil || [];
  const mkOutcome = useMemo(
    () => hasil.find((item) => item.jenis === 'Mata kuliah') || null,
    [hasil],
  );
  const cpmkOutcomes = useMemo(
    () => hasil.filter((item) => item.jenis === 'CPMK'),
    [hasil],
  );
  const cplOutcomes = useMemo(
    () => hasil.filter((item) => item.jenis === 'CPL'),
    [hasil],
  );

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Rincian Nilai & Capaian
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1.5">
            Rincian nilai instrumen pribadi (read-only). Nilai yang belum diinput ditandai{' '}
            <strong className="text-[#15333A]">—</strong> dan tidak pernah dianggap nol.
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="mahasiswa-mk-filter"
            className="text-[11.5px] font-semibold text-[#566B70]"
          >
            Tampilkan mata kuliah
          </label>
          <select
            id="mahasiswa-mk-filter"
            aria-label="Tampilkan mata kuliah"
            value={activeClassId}
            onChange={(e) => setSearchParams({ kelas: e.target.value })}
            disabled={isTikOrInactive || classes.length === 0}
            className="min-w-[260px] h-[38px] px-3 rounded-[8px] bg-white border border-[#E4DFD4] text-[12.5px] font-semibold text-[#15333A] disabled:opacity-50 focus:outline-none focus:border-[#15333A]"
          >
            {isTikOrInactive || classes.length === 0 ? (
              <option value="">Tidak ada mata kuliah paket</option>
            ) : (
              classes.map((cls) => (
                <option key={cls.id} value={cls.id}>
                  {cls.nama_mk} · {cls.kelas}
                </option>
              ))
            )}
          </select>
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

      {loadingWorkspace || loadingDetail ? (
        <LoadingSkeleton variant="dashboard" />
      ) : !selectedPeriod ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada data periode akademik.
        </div>
      ) : isTikOrInactive ? (
        <EmptyTikState
          period={selectedPeriod}
          classLabel={selectedPeriod.kelas}
          studentStatus={selectedPeriod.status_mahasiswa}
          hasOtherPeriods={periods.length > 1}
        />
      ) : !detail ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada paket mata kuliah yang dapat ditampilkan pada periode ini.
        </div>
      ) : (
        <>
          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2 text-[12px]">
                <span className="font-semibold text-[#CC6E38]">
                  {detail.kode_mk}
                </span>
                <span className="text-[#7A8C90]">·</span>
                <span className="text-[#566B70]">
                  {detail.kelas} · Semester {detail.semester_mk} ({detail.sks}{' '}
                  SKS)
                </span>
                <span
                  className={[
                    'px-2 py-0.5 rounded-full text-[11px] font-semibold',
                    detail.siap_dinilai
                      ? 'bg-[#E6F2EE] text-[#1A5C4D]'
                      : 'bg-[#F7EAE1] text-[#B55824]',
                  ].join(' ')}
                >
                  {detail.siap_dinilai
                    ? 'Rancangan Siap Dinilai (100%)'
                    : `Draft (${formatIndonesianPercent(detail.total_bobot)})`}
                </span>
              </div>
              <h2 className="text-[20px] font-semibold text-[#15333A]">
                {detail.nama_mk}
              </h2>
              <p className="text-[13px] text-[#566B70]">
                Dosen Pengampu: <strong className="text-[#15333A]">{detail.dosen_nama}</strong>
              </p>
            </div>

            <div className="p-4 rounded-[10px] bg-[#FAF8F3] border border-[#E4DFD4] min-w-[200px] text-right">
              <p className="text-[11.5px] font-medium text-[#566B70]">
                Capaian Mata Kuliah Anda
              </p>
              <p className="text-[28px] font-semibold text-[#15333A] tabular-nums mt-0.5">
                {formatIndonesianPercent(mkOutcome?.capaian)}
              </p>
              <p className="text-[11px] text-[#7A8C90]">
                {mkOutcome
                  ? `${mkOutcome.instrumen_lengkap} / ${mkOutcome.total_instrumen} instrumen terisi · ${mkOutcome.status}`
                  : '—'}
              </p>
            </div>
          </section>

          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
            <h2 className="text-[18px] font-semibold text-[#15333A]">
              Rincian Nilai Instrumen ({detail.instrumen.length})
            </h2>

            {detail.instrumen.length === 0 ? (
              <p className="text-[13px] text-[#566B70]">
                Dosen pengampu belum menambahkan instrumen penilaian pada rancangan mata kuliah ini.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                      <th className="py-3 pr-4">CPMK</th>
                      <th className="py-3 pr-4">Sub-CPMK</th>
                      <th className="py-3 pr-4">Instrumen Penilaian</th>
                      <th className="py-3 pr-4">CPL Terkait</th>
                      <th className="py-3 pr-4 text-right">Bobot</th>
                      <th className="py-3 pr-4 text-right">Nilai Mentah</th>
                      <th className="py-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                    {detail.instrumen.map((item) => (
                      <tr key={item.instrumen_id} className="hover:bg-[#FAF8F3]/70">
                        <td className="py-3 pr-4 font-semibold text-[#15333A] whitespace-nowrap">
                          {item.kode_cpmk}
                        </td>
                        <td className="py-3 pr-4 text-[#566B70] whitespace-nowrap">
                          {item.kode_sub}
                        </td>
                        <td className="py-3 pr-4 font-medium text-[#15333A]">
                          {item.nama_instrumen}
                        </td>
                        <td className="py-3 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {item.cpl_kodes.length > 0 ? (
                              item.cpl_kodes.map((code) => (
                                <span
                                  key={code}
                                  className="px-2 py-0.5 rounded-full bg-[#E6F0EE] text-[#15333A] text-[11px] font-semibold"
                                >
                                  {code}
                                </span>
                              ))
                            ) : (
                              <span className="text-[#7A8C90]">—</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-[#334B51] whitespace-nowrap">
                          {formatIndonesianPercent(item.bobot_persentase)}
                        </td>
                        <td className="py-3 pr-4 text-right font-semibold tabular-nums text-[#15333A] whitespace-nowrap">
                          {formatIndonesianScore(item.nilai_mentah)}
                        </td>
                        <td className="py-3 text-right whitespace-nowrap">
                          <span
                            className={[
                              'inline-flex items-center h-6 px-2.5 rounded-full text-[11.5px] font-semibold',
                              item.status === 'Sudah diinput'
                                ? 'bg-[#E6F2EE] text-[#1A5C4D]'
                                : 'bg-[#F7EAE1] text-[#B55824]',
                            ].join(' ')}
                          >
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
              <h2 className="text-[18px] font-semibold text-[#15333A]">
                Capaian per CPMK
              </h2>
              {cpmkOutcomes.length === 0 ? (
                <p className="text-[13px] text-[#566B70]">
                  Belum ada CPMK pada rancangan ini.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {cpmkOutcomes.map((cpmk) => (
                    <div
                      key={cpmk.id}
                      className="p-3.5 rounded-[10px] bg-[#FAF8F3] border border-[#EFECE4] flex items-start justify-between gap-4"
                    >
                      <div className="min-w-0">
                        <p className="text-[13px] font-semibold text-[#15333A]">
                          {cpmk.kode}
                        </p>
                        <p className="text-[12px] text-[#566B70] mt-0.5">
                          {cpmk.label}
                        </p>
                        <p className="text-[11px] text-[#7A8C90] mt-1">
                          {cpmk.instrumen_lengkap} / {cpmk.total_instrumen}{' '}
                          instrumen terisi · {cpmk.status}
                        </p>
                      </div>
                      <span className="text-[15px] font-semibold text-[#15333A] tabular-nums shrink-0">
                        {formatIndonesianPercent(cpmk.capaian)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
              <div>
                <h2 className="text-[18px] font-semibold text-[#15333A]">
                  Kontribusi CPL Mata Kuliah
                </h2>
                <p className="text-[12px] text-[#566B70] mt-0.5">
                  Capaian aktual pada mata kuliah ini (tanpa garis target).
                </p>
              </div>
              {cplOutcomes.length === 0 ? (
                <p className="text-[13px] text-[#566B70]">
                  Belum ada CPL terpetakan pada mata kuliah ini.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {cplOutcomes.map((cpl) => {
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
                        <p className="text-[12px] text-[#566B70] line-clamp-2">
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
          </div>
        </>
      )}
    </div>
  );
}
