import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import RadarCapaianChart from '../../components/dashboard/RadarCapaianChart.jsx';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import { getKelasMkCapaian } from '../../lib/adminApi.js';

export default function DosenDashboardPage() {
  const {
    periodDesigns,
    selectedPeriod,
    classes,
    loadingWorkspace,
    workspaceError,
    refreshDosenWorkspace,
  } = useDosenWorkspace();

  const [attainmentByClass, setAttainmentByClass] = useState({});
  const [loadingAttainment, setLoadingAttainment] = useState(false);
  const [selectedClassId, setSelectedClassId] = useState('');

  useEffect(() => {
    setSelectedClassId((prev) =>
      prev && classes.some((c) => c.id === prev) ? prev : classes[0]?.id || '',
    );
  }, [classes]);

  const loadAttainments = useCallback(async () => {
    if (classes.length === 0) {
      setAttainmentByClass({});
      return;
    }
    setLoadingAttainment(true);
    try {
      const entries = await Promise.all(
        classes.map(async (cls) => {
          try {
            const data = await getKelasMkCapaian(cls.id);
            return [cls.id, data];
          } catch {
            return [cls.id, null];
          }
        }),
      );
      setAttainmentByClass(Object.fromEntries(entries));
    } finally {
      setLoadingAttainment(false);
    }
  }, [classes]);

  useEffect(() => {
    loadAttainments();
  }, [loadAttainments]);

  const designById = useMemo(
    () => Object.fromEntries(periodDesigns.map((d) => [d.id, d])),
    [periodDesigns],
  );

  const distinctMkCount = useMemo(
    () => new Set(classes.map((c) => c.kurikulum_mk_id)).size,
    [classes],
  );

  const participantStats = useMemo(() => {
    let complete = 0;
    let total = 0;
    for (const cls of classes) {
      const data = attainmentByClass[cls.id];
      const mkNode = data?.rekap?.find((item) => item.jenis === 'Mata kuliah');
      if (mkNode) {
        complete += mkNode.mahasiswa_lengkap;
        total += mkNode.total_mahasiswa;
      } else if (data?.peserta) {
        total += data.peserta.length;
      }
    }
    return { complete, total };
  }, [attainmentByClass, classes]);

  const readyDesigns = useMemo(
    () => periodDesigns.filter((d) => d.siap_dinilai),
    [periodDesigns],
  );

  const readyClassesCount = useMemo(
    () => classes.filter((c) => designById[c.rancangan_id]?.siap_dinilai).length,
    [classes, designById],
  );

  const selectedClass =
    classes.find((c) => c.id === selectedClassId) || classes[0] || null;
  const selectedAttainment = selectedClass
    ? attainmentByClass[selectedClass.id]
    : null;
  const selectedCpmkNodes = useMemo(
    () =>
      (selectedAttainment?.rekap || []).filter((item) => item.jenis === 'CPMK'),
    [selectedAttainment],
  );
  const selectedMkNode = useMemo(
    () =>
      (selectedAttainment?.rekap || []).find(
        (item) => item.jenis === 'Mata kuliah',
      ) || null,
    [selectedAttainment],
  );

  const activeDesign =
    (selectedClass && designById[selectedClass.rancangan_id]) ||
    periodDesigns[0] ||
    null;

  const activeDesignMkName = useMemo(() => {
    if (!activeDesign) return '';
    const match = classes.find((c) => c.rancangan_id === activeDesign.id);
    return match?.nama_mk || 'Mata kuliah';
  }, [activeDesign, classes]);

  const isBusy = loadingWorkspace || loadingAttainment;

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
          Dashboard Dosen
        </h1>
        <p className="text-[14px] leading-[17px] text-[#737373] dark:text-[#A3A3A0]">
          Seluruh kelas penugasan Anda pada periode terpilih.
        </p>
      </div>

      {workspaceError && (
        <div
          role="alert"
          className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-4 flex items-center justify-between gap-4 text-[13px]"
        >
          <span className="text-[#B55824] dark:text-[#F0C3A4]">
            {workspaceError}
          </span>
          <button
            type="button"
            onClick={refreshDosenWorkspace}
            className="h-8 px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] font-medium cursor-pointer"
          >
            Muat ulang
          </button>
        </div>
      )}

      {/* 4 Kartu Statistik */}
      <div className="grid grid-cols-4 gap-6">
        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Kelas MK diampu
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums">
            {isBusy ? '…' : classes.length}
          </p>
          <p className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
            {distinctMkCount} mata kuliah
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Peserta per kelas MK
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums">
            {isBusy ? '…' : participantStats.total}
          </p>
          <p className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
            Total peserta periode ini
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Rancangan siap dinilai
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums">
            {isBusy ? '…' : `${readyDesigns.length} / ${periodDesigns.length}`}
          </p>
          <p className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
            Dipakai oleh {readyClassesCount} kelas MK
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Peserta dengan nilai lengkap
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums">
            {isBusy
              ? '…'
              : `${participantStats.complete} / ${participantStats.total}`}
          </p>
          <p className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
            Dihitung per kelas MK
          </p>
        </div>
      </div>

      {/* Baris Tengah */}
      <div className="grid grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,744fr)_minmax(0,368fr)] gap-6">
        <section className="min-h-[380px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col">
          <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
            Kelas yang diampu
          </h2>
          <p className="text-[12px] text-[#737373] dark:text-[#A3A3A0] mt-1.5">
            Semua kelas pada periode ini · Filter di kanan hanya berlaku untuk
            rekap.
          </p>

          {isBusy ? (
            <div className="mt-6 space-y-4">
              {[1, 2, 3].map((row) => (
                <div
                  key={row}
                  className="h-9 rounded bg-[#F5F5F4] dark:bg-[#2A2A27] animate-pulse"
                />
              ))}
            </div>
          ) : classes.length === 0 ? (
            <div className="flex-1 flex items-center text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Belum ada kelas penugasan pada periode ini.
            </div>
          ) : (
            <div className="mt-6 flex-1 flex flex-col">
              <div className="grid grid-cols-[minmax(120px,1fr)_72px_58px_138px] gap-2 xl:grid-cols-[minmax(0,1fr)_105px_120px_175px] xl:gap-4 pb-3 border-b border-[#E5E5E5] dark:border-[#2E2E2B] text-[11px] font-medium text-[#737373] dark:text-[#A3A3A0]">
                <span>Mata kuliah / kelas</span>
                <span>Rancangan</span>
                <span>Peserta lengkap</span>
                <span>Tindakan</span>
              </div>

              <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
                {classes.map((cls) => {
                  const design = designById[cls.rancangan_id];
                  const mkNode = attainmentByClass[cls.id]?.rekap?.find(
                    (r) => r.jenis === 'Mata kuliah',
                  );
                  const complete = mkNode?.mahasiswa_lengkap ?? 0;
                  const total =
                    mkNode?.total_mahasiswa ??
                    attainmentByClass[cls.id]?.peserta?.length ??
                    0;
                  const isReady = Boolean(design?.siap_dinilai);
                  const allComplete = total > 0 && complete === total;

                  return (
                    <div
                      key={cls.id}
                      className="grid grid-cols-[minmax(120px,1fr)_72px_58px_138px] gap-2 xl:grid-cols-[minmax(0,1fr)_105px_120px_175px] xl:gap-4 py-4 items-center"
                    >
                      <span className="text-[13px] text-[#252525] dark:text-[#F5F5F4] truncate">
                        {cls.nama_mk} · {cls.kelas}
                      </span>
                      <span
                        className={
                          isReady
                            ? 'text-[12px] text-[#737373] dark:text-[#A3A3A0]'
                            : 'text-[12px] font-medium text-[#B55824] dark:text-[#F0C3A4]'
                        }
                      >
                        {isReady ? 'Siap dinilai' : 'Belum siap'}
                      </span>
                      <span className="text-[12px] tabular-nums text-[#737373] dark:text-[#A3A3A0]">
                        {complete} / {total}
                      </span>
                      <div className="whitespace-nowrap">
                        {!isReady ? (
                          <Link
                            to={`/dosen/rancangan/${cls.rancangan_id}`}
                            className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline"
                          >
                            Lengkapi rancangan →
                          </Link>
                        ) : allComplete || design?.periode_ditutup ? (
                          <Link
                            to={`/dosen/capaian?kelas=${cls.id}`}
                            className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline"
                          >
                            Lihat rekap {cls.kelas} →
                          </Link>
                        ) : (
                          <Link
                            to={`/dosen/nilai/${cls.id}`}
                            className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline"
                          >
                            Input nilai {cls.kelas} →
                          </Link>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="min-h-[380px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between gap-4">
          <div className="flex flex-col gap-3">
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
              Rekap kelas · CPMK
            </h2>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="dosen-dashboard-mk-filter"
                className="text-[12px] text-[#737373] dark:text-[#A3A3A0]"
              >
                Tampilkan mata kuliah
              </label>
              <select
                id="dosen-dashboard-mk-filter"
                value={selectedClass?.id || ''}
                onChange={(e) => setSelectedClassId(e.target.value)}
                disabled={classes.length === 0}
                className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[12px] font-medium"
              >
                {classes.length === 0 ? (
                  <option value="">Belum ada kelas</option>
                ) : (
                  classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>
                      {cls.nama_mk} · {cls.kelas}
                    </option>
                  ))
                )}
              </select>
            </div>

            {isBusy ? (
              <div className="h-[176px] rounded bg-[#F5F5F4] dark:bg-[#2A2A27] animate-pulse" />
            ) : (
              <RadarCapaianChart
                items={selectedCpmkNodes}
                compact
                emptyMessage="Belum ada CPMK pada rancangan kelas ini."
              />
            )}
          </div>

          {selectedClass && (
            <div className="flex flex-col gap-1 pt-2 border-t border-[#E5E5E5] dark:border-[#2E2E2B]">
              <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                {selectedMkNode?.mahasiswa_lengkap ?? 0} dari{' '}
                {selectedMkNode?.total_mahasiswa ?? 0} peserta lengkap
              </p>
              <p className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                {selectedPeriod
                  ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester}`
                  : ''}{' '}
                · {selectedClass.kelas}
              </p>
            </div>
          )}
        </section>
      </div>

      {/* Baris Bawah */}
      {activeDesign && (
        <section className="min-h-[164px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between gap-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
              Rancangan bersama · {activeDesignMkName}
            </h2>
            <p className="text-[12px] text-[#737373] dark:text-[#A3A3A0] mt-1.5">
              Dipakai oleh{' '}
              {activeDesign.kelas_pengguna.map((k) => k.label).join(' dan ')}.{' '}
              {activeDesign.struktur_terkunci
                ? activeDesign.alasan_terkunci
                : 'Struktur masih dapat disusun sebelum nilai pertama masuk.'}
            </p>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-8 text-[13px]">
              <span>
                {activeDesign.siap_dinilai
                  ? 'Pemetaan CPMK–CPL lengkap'
                  : activeDesign.alasan_belum_siap[0] ||
                    'Pemetaan CPMK–CPL belum lengkap'}
              </span>
              <span>
                Total bobot instrumen {Number(activeDesign.total_bobot).toFixed(2).replace('.', ',')}%
              </span>
            </div>

            <Link
              to={`/dosen/rancangan/${activeDesign.id}`}
              className="h-[38px] px-4 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium inline-flex items-center shrink-0"
            >
              Lihat rancangan {activeDesignMkName} →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
