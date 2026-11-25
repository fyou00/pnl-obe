import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  getMatriksMk,
  getPaketPreview,
  listAngkatan,
  listCpl,
  listKelasPeriode,
  listPaketMk,
} from '../../lib/adminApi.js';

export default function AdminDashboardPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedCurriculum,
    selectedPeriodId,
    selectedPeriod,
    loadingMeta,
    metaError,
    reloadWorkspaceMeta,
  } = useAdminWorkspace();

  const [cohorts, setCohorts] = useState([]);
  const [cpls, setCpls] = useState([]);
  const [paketCourses, setPaketCourses] = useState([]);
  const [matrixCounts, setMatrixCounts] = useState({});
  const [periodClasses, setPeriodClasses] = useState([]);
  const [assignmentResults, setAssignmentResults] = useState([]);

  const [loadingData, setLoadingData] = useState(false);
  const [dataError, setDataError] = useState('');

  const loadDashboardData = useCallback(async () => {
    if (loadingMeta) return;
    setLoadingData(true);
    setDataError('');

    try {
      const [cohortsData, cplsData, coursesData, classesData] = await Promise.all([
        listAngkatan({ limit: 100 }),
        selectedCurriculumId
          ? listCpl(selectedCurriculumId, { limit: 100 })
          : Promise.resolve([]),
        selectedCurriculumId
          ? listPaketMk(selectedCurriculumId, { limit: 100 })
          : Promise.resolve([]),
        selectedPeriodId
          ? listKelasPeriode(selectedPeriodId, { limit: 100 })
          : Promise.resolve([]),
      ]);

      setCohorts(cohortsData);
      setCpls(cplsData);
      setPaketCourses(coursesData);
      setPeriodClasses(classesData);

      if (selectedCurriculumId && coursesData.length > 0) {
        const matrices = await Promise.all(
          coursesData.map(async (course) => {
            try {
              const items = await getMatriksMk(selectedCurriculumId, course.id);
              return [course.id, items.length];
            } catch {
              return [course.id, 0];
            }
          }),
        );
        setMatrixCounts(Object.fromEntries(matrices));
      } else {
        setMatrixCounts({});
      }

      if (selectedPeriodId && classesData.length > 0 && cohortsData.length > 0) {
        const regularClasses = classesData.filter((c) => c.kode_kelas !== 'K');
        const cohortIdsWithRegular = [
          ...new Set(regularClasses.map((c) => c.angkatan_id)),
        ];
        const cohortById = Object.fromEntries(cohortsData.map((c) => [c.id, c]));

        const previews = await Promise.all(
          cohortIdsWithRegular.map(async (angkatanId) => {
            const cohort = cohortById[angkatanId];
            try {
              const preview = await getPaketPreview(selectedPeriodId, angkatanId);
              return { cohort, preview, error: null };
            } catch (err) {
              return {
                cohort,
                preview: null,
                error: err.message || 'Belum dapat memuat kesiapan penugasan.',
              };
            }
          }),
        );
        setAssignmentResults(previews);
      } else {
        setAssignmentResults([]);
      }
    } catch (err) {
      setDataError(err.message || 'Gagal memuat data dashboard.');
    } finally {
      setLoadingData(false);
    }
  }, [loadingMeta, selectedCurriculumId, selectedPeriodId]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const curriculumCohorts = useMemo(() => {
    if (!selectedCurriculumId) return cohorts;
    return cohorts.filter((c) => c.kurikulum_id === selectedCurriculumId);
  }, [cohorts, selectedCurriculumId]);

  const latestCohort = useMemo(() => {
    if (curriculumCohorts.length === 0) return null;
    return [...curriculumCohorts].sort(
      (a, b) => b.tahun_masuk - a.tahun_masuk,
    )[0];
  }, [curriculumCohorts]);

  const regularClasses = useMemo(() => {
    const allRegular = periodClasses.filter((c) => c.kode_kelas !== 'K');
    if (curriculumCohorts.length === 0) return allRegular;
    const cohortIds = new Set(curriculumCohorts.map((c) => c.id));
    const matching = allRegular.filter((c) => cohortIds.has(c.angkatan_id));
    return matching.length > 0 ? matching : allRegular;
  }, [curriculumCohorts, periodClasses]);

  const activeSemesters = useMemo(() => {
    return [
      ...new Set(
        regularClasses
          .map((c) => c.semester_studi)
          .filter((sem) => sem !== null && sem !== undefined),
      ),
    ].sort((a, b) => a - b);
  }, [regularClasses]);

  const displayedCourses = useMemo(() => {
    if (activeSemesters.length === 1) {
      const filtered = paketCourses.filter(
        (c) => c.semester === activeSemesters[0],
      );
      if (filtered.length > 0) return filtered;
    }
    return paketCourses;
  }, [activeSemesters, paketCourses]);

  const packageCourseCount =
    activeSemesters.length === 1
      ? paketCourses.filter((c) => c.semester === activeSemesters[0]).length
      : paketCourses.length;

  const isBusy = loadingMeta || loadingData;

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      {/* Header halaman */}
      <div className="flex items-start justify-between gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Dashboard Admin
          </h1>
          <p className="text-[14px] leading-[17px] text-[#737373] dark:text-[#A3A3A0]">
            Pantau pembebanan CPL dan pelaksanaan paket pada periode terpilih.
          </p>
        </div>

        <div className="pt-1">
          <label htmlFor="dashboard-kurikulum-select" className="sr-only">
            Pilih versi kurikulum
          </label>
          <select
            id="dashboard-kurikulum-select"
            aria-label="Pilih versi kurikulum"
            value={selectedCurriculumId}
            onChange={(e) => setSelectedCurriculumId(e.target.value)}
            disabled={curricula.length === 0}
            className="min-w-[218px] h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] focus:outline-none focus:ring-2 focus:ring-[#252525]/20 dark:focus:ring-[#F5F5F4]/20 disabled:opacity-60"
          >
            {curricula.length === 0 ? (
              <option value="">Belum ada kurikulum</option>
            ) : (
              curricula.map((curriculum) => (
                <option key={curriculum.id} value={curriculum.id}>
                  {curriculum.nama} ({curriculum.status})
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {(metaError || dataError) && (
        <div
          role="alert"
          className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-4 flex items-center justify-between gap-4 text-[13px]"
        >
          <span className="text-[#B55824] dark:text-[#F0C3A4]">
            {metaError || dataError}
          </span>
          <button
            type="button"
            onClick={metaError ? reloadWorkspaceMeta : loadDashboardData}
            className="h-8 px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] font-medium hover:bg-[#F5F5F4] dark:hover:bg-[#2A2A27] cursor-pointer"
          >
            Muat ulang
          </button>
        </div>
      )}

      {/* 4 Kartu Statistik */}
      <div className="grid grid-cols-4 gap-6">
        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] leading-[16px] text-[#737373] dark:text-[#A3A3A0]">
            Angkatan
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
            {isBusy ? '…' : latestCohort ? latestCohort.tahun_masuk : '—'}
          </p>
          <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0] truncate">
            {selectedCurriculum
              ? `${selectedCurriculum.nama}${curriculumCohorts.length > 0 ? ` · ${curriculumCohorts.length} angkatan` : ''}`
              : 'Belum ada versi kurikulum'}
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] leading-[16px] text-[#737373] dark:text-[#A3A3A0]">
            Master CPL
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
            {isBusy ? '…' : cpls.length}
          </p>
          <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Dalam versi kurikulum
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] leading-[16px] text-[#737373] dark:text-[#A3A3A0]">
            Mata kuliah
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
            {isBusy ? '…' : packageCourseCount}
          </p>
          <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0]">
            {activeSemesters.length === 1
              ? `Dalam paket semester ${activeSemesters[0]}`
              : 'Total MK dalam kurikulum'}
          </p>
        </div>

        <div className="min-h-[132px] p-5 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
          <p className="text-[13px] leading-[16px] text-[#737373] dark:text-[#A3A3A0]">
            Kelas reguler
          </p>
          <p className="text-[30px] font-semibold leading-[36px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
            {isBusy ? '…' : regularClasses.length}
          </p>
          <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0]">
            {activeSemesters.length > 0
              ? `Semester ${activeSemesters.join(', ')} · A–E`
              : 'Belum ada kelas pada periode ini'}
          </p>
        </div>
      </div>

      {/* Baris Tengah */}
      <div className="grid grid-cols-[minmax(0,744fr)_minmax(0,368fr)] gap-6">
        <section className="min-h-[380px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col">
          <h2 className="text-[17px] font-semibold leading-[21px] text-[#252525] dark:text-[#F5F5F4]">
            Kesiapan kurikulum
          </h2>
          <p className="text-[12px] leading-[15px] text-[#737373] dark:text-[#A3A3A0] mt-1.5">
            Pembebanan CPL per mata kuliah ·{' '}
            {selectedCurriculum?.nama || 'Belum ada kurikulum'}
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
          ) : displayedCourses.length === 0 ? (
            <div className="flex-1 flex flex-col items-start justify-center gap-3 py-8">
              <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                Belum ada paket mata kuliah pada versi kurikulum ini.
              </p>
              <Link
                to="/admin/mata-kuliah"
                className="text-[12.5px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline"
              >
                Kelola paket mata kuliah →
              </Link>
            </div>
          ) : (
            <div className="mt-6 flex-1 flex flex-col">
              <div className="grid grid-cols-[minmax(140px,1fr)_68px_68px_108px] gap-2 xl:grid-cols-[minmax(0,1fr)_90px_90px_140px] xl:gap-4 pb-3 border-b border-[#E5E5E5] dark:border-[#2E2E2B] text-[11px] font-medium text-[#737373] dark:text-[#A3A3A0]">
                <span>Mata kuliah</span>
                <span>Jumlah CPL</span>
                <span>Semester</span>
                <span>Pembebanan</span>
              </div>

              <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
                {displayedCourses.slice(0, 6).map((course) => {
                  const count = matrixCounts[course.id] ?? 0;
                  return (
                    <div
                      key={course.id}
                      className="grid grid-cols-[minmax(140px,1fr)_68px_68px_108px] gap-2 xl:grid-cols-[minmax(0,1fr)_90px_90px_140px] xl:gap-4 py-4 items-center"
                    >
                      <span className="text-[13px] text-[#252525] dark:text-[#F5F5F4] truncate">
                        {course.nama_mk}
                      </span>
                      <span className="text-[14px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
                        {count}
                      </span>
                      <span className="text-[14px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
                        {course.semester}
                      </span>
                      <span
                        className={
                          count > 0
                            ? 'text-[12px] text-[#737373] dark:text-[#A3A3A0]'
                            : 'text-[12px] font-medium text-[#B55824] dark:text-[#F0C3A4]'
                        }
                      >
                        {count > 0 ? 'Lengkap' : 'Belum dipetakan'}
                      </span>
                    </div>
                  );
                })}
              </div>

              {displayedCourses.length > 6 && (
                <div className="pt-3 mt-auto">
                  <Link
                    to="/admin/matriks"
                    className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline"
                  >
                    Lihat semua {displayedCourses.length} mata kuliah di matriks →
                  </Link>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="min-h-[380px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col">
          <h2 className="text-[17px] font-semibold leading-[21px] text-[#252525] dark:text-[#F5F5F4]">
            Akses cepat
          </h2>
          <p className="text-[12px] leading-[15px] text-[#737373] dark:text-[#A3A3A0] mt-1.5">
            Kurikulum dan pelaksanaan akademik.
          </p>

          <div className="mt-7 flex flex-col gap-5">
            <Link
              to="/admin/cpl"
              className="h-[38px] px-3 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium flex items-center hover:opacity-90 transition-opacity"
            >
              Kelola Master CPL →
            </Link>
            <Link
              to="/admin/matriks"
              className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[#252525] dark:text-[#F5F5F4] text-[12px] font-medium flex items-center hover:bg-[#F5F5F4] dark:hover:bg-[#2A2A27] transition-colors"
            >
              Atur matriks pembebanan →
            </Link>
            <Link
              to="/admin/paket"
              className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[#252525] dark:text-[#F5F5F4] text-[12px] font-medium flex items-center hover:bg-[#F5F5F4] dark:hover:bg-[#2A2A27] transition-colors"
            >
              Kelola paket dan penugasan →
            </Link>
            <Link
              to="/admin/laporan"
              className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[#252525] dark:text-[#F5F5F4] text-[12px] font-medium flex items-center hover:bg-[#F5F5F4] dark:hover:bg-[#2A2A27] transition-colors"
            >
              Lihat laporan OBE →
            </Link>
          </div>
        </section>
      </div>

      {/* Baris Bawah — Kesiapan penugasan kelas MK */}
      <section className="min-h-[164px] p-6 rounded-[12px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-[17px] font-semibold leading-[21px] text-[#252525] dark:text-[#F5F5F4]">
              Kesiapan penugasan kelas MK
            </h2>
            <p className="text-[12px] leading-[15px] text-[#737373] dark:text-[#A3A3A0] mt-1.5">
              {selectedPeriod
                ? `Periode ${selectedPeriod.tahun_akademik} ${selectedPeriod.semester}`
                : 'Belum ada periode akademik terpilih'}
            </p>
          </div>

          <Link
            to="/admin/paket"
            className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline shrink-0"
          >
            Buka paket &amp; penugasan →
          </Link>
        </div>

        {isBusy ? (
          <div className="h-9 rounded bg-[#F5F5F4] dark:bg-[#2A2A27] animate-pulse" />
        ) : !selectedPeriod ? (
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Buat periode akademik terlebih dahulu pada menu{' '}
            <Link to="/admin/periode" className="underline text-[#252525] dark:text-[#F5F5F4]">
              Periode akademik
            </Link>
            .
          </p>
        ) : assignmentResults.length === 0 ? (
          <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Belum ada kelas reguler pada periode terpilih. Tambahkan kelas di menu{' '}
            <Link to="/admin/angkatan" className="underline text-[#252525] dark:text-[#F5F5F4]">
              Angkatan dan kelas
            </Link>
            .
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {assignmentResults.map(({ cohort, preview, error }) => {
              if (error) {
                return (
                  <div
                    key={cohort?.id || 'unknown'}
                    className="flex items-center justify-between gap-4 py-1 text-[13px]"
                  >
                    <span className="text-[#252525] dark:text-[#F5F5F4] font-medium">
                      Angkatan {cohort?.tahun_masuk ?? '—'}
                    </span>
                    <span className="text-[#B55824] dark:text-[#F0C3A4]">
                      {error}
                    </span>
                  </div>
                );
              }

              const courseById = Object.fromEntries(
                preview.mata_kuliah.map((m) => [m.kurikulum_mk_id, m]),
              );
              const classById = Object.fromEntries(
                preview.kelas.map((k) => [k.kelas_periode_id, k]),
              );
              const unassigned = preview.penugasan.filter(
                (pair) => pair.dosen_id === null,
              );

              if (unassigned.length === 0) {
                return (
                  <div
                    key={cohort.id}
                    className="flex items-center justify-between gap-4 py-1 text-[13px]"
                  >
                    <span className="text-[#252525] dark:text-[#F5F5F4]">
                      Paket semester {preview.semester_studi} · Angkatan{' '}
                      {cohort.tahun_masuk}
                    </span>
                    <span className="text-[#1A5C4D] dark:text-[#86EFAC] font-medium">
                      Seluruh {preview.penugasan.length} kelas MK sudah memiliki dosen
                    </span>
                  </div>
                );
              }

              return (
                <div key={cohort.id} className="flex flex-col divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
                  {unassigned.slice(0, 5).map((pair) => {
                    const course = courseById[pair.kurikulum_mk_id];
                    const klass = classById[pair.kelas_periode_id];
                    return (
                      <div
                        key={`${pair.kelas_periode_id}-${pair.kurikulum_mk_id}`}
                        className="grid grid-cols-[minmax(0,330px)_minmax(0,340px)_1fr] items-center gap-6 py-2 text-[13px]"
                      >
                        <span className="text-[#252525] dark:text-[#F5F5F4] truncate">
                          {course?.nama_mk || 'Mata kuliah'} · {klass?.label || 'Kelas'}
                        </span>
                        <span className="text-[#252525] dark:text-[#F5F5F4]">
                          Pengampu belum ditetapkan
                        </span>
                        <Link
                          to="/admin/paket"
                          className="text-[#737373] dark:text-[#A3A3A0] hover:text-[#252525] dark:hover:text-[#F5F5F4]"
                        >
                          Tetapkan dosen →
                        </Link>
                      </div>
                    );
                  })}
                  {unassigned.length > 5 && (
                    <div className="pt-2 text-[12px] text-[#737373] dark:text-[#A3A3A0]">
                      +{unassigned.length - 5} kelas MK lainnya belum ditetapkan.
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0]">
        Periode:{' '}
        {selectedPeriod
          ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester} (${selectedPeriod.status})`
          : 'Belum dipilih'}{' '}
        · Versi kurikulum:{' '}
        {selectedCurriculum
          ? `${selectedCurriculum.nama} (${selectedCurriculum.status})`
          : 'Belum dipilih'}
      </p>
    </div>
  );
}
