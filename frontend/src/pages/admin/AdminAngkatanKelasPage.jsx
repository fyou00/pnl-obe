import { useCallback, useEffect, useState } from 'react';
import { LockedPeriodBanner } from '../../components/states/SystemStates.jsx';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  createAngkatan,
  createKelasPeriode,
  createRoster,
  deleteAngkatan,
  deleteKelasPeriode,
  deleteRoster,
  linkAngkatanMahasiswa,
  listAngkatan,
  listAngkatanMahasiswa,
  listKelasPeriode,
  listRoster,
  updateRoster,
} from '../../lib/adminApi.js';

const KODE_KELAS_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'K'];
const STATUS_MAHASISWA_OPTIONS = ['Aktif', 'Cuti', 'Nonaktif'];

export default function AdminAngkatanKelasPage() {
  const { curricula, selectedPeriodId, selectedPeriod } = useAdminWorkspace();

  const [cohorts, setCohorts] = useState([]);
  const [selectedCohortId, setSelectedCohortId] = useState('');
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);
  const [roster, setRoster] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyKey, setBusyKey] = useState('');

  const activeCurricula = curricula.filter((c) => c.status === 'Aktif');
  const curriculumById = Object.fromEntries(curricula.map((c) => [c.id, c]));

  const [cohortForm, setCohortForm] = useState({
    tahun_masuk: new Date().getFullYear(),
    kurikulum_id: '',
  });
  const [classForm, setClassForm] = useState({
    angkatan_id: '',
    kode_kelas: 'A',
    semester_studi: 1,
  });
  const [linkUserId, setLinkUserId] = useState('');
  const [rosterForm, setRosterForm] = useState({
    mahasiswa_id: '',
    kelas_periode_id: '',
    status: 'Aktif',
  });

  useEffect(() => {
    if (!cohortForm.kurikulum_id && activeCurricula[0]?.id) {
      setCohortForm((prev) => ({
        ...prev,
        kurikulum_id: activeCurricula[0].id,
      }));
    }
  }, [activeCurricula, cohortForm.kurikulum_id]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [cohortsData, classesData, rosterData] = await Promise.all([
        listAngkatan({ limit: 100 }),
        selectedPeriodId
          ? listKelasPeriode(selectedPeriodId, { limit: 100 })
          : Promise.resolve([]),
        selectedPeriodId
          ? listRoster(selectedPeriodId, { limit: 100 })
          : Promise.resolve([]),
      ]);
      setCohorts(cohortsData);
      setClasses(classesData);
      setRoster(rosterData);

      const defaultCohort =
        selectedCohortId && cohortsData.some((c) => c.id === selectedCohortId)
          ? selectedCohortId
          : cohortsData[0]?.id || '';
      setSelectedCohortId(defaultCohort);
      setClassForm((prev) => ({
        ...prev,
        angkatan_id:
          prev.angkatan_id && cohortsData.some((c) => c.id === prev.angkatan_id)
            ? prev.angkatan_id
            : defaultCohort,
      }));

      if (defaultCohort) {
        const studentData = await listAngkatanMahasiswa(defaultCohort, {
          limit: 100,
        });
        setStudents(studentData);
      } else {
        setStudents([]);
      }
    } catch (err) {
      setError(err.message || 'Gagal memuat data angkatan dan kelas.');
    } finally {
      setLoading(false);
    }
  }, [selectedCohortId, selectedPeriodId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCohortChange = async (cohortId) => {
    setSelectedCohortId(cohortId);
    if (!cohortId) {
      setStudents([]);
      return;
    }
    try {
      const data = await listAngkatanMahasiswa(cohortId, { limit: 100 });
      setStudents(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat mahasiswa angkatan.');
    }
  };

  const handleCreateCohort = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyKey('create-cohort');
    try {
      const created = await createAngkatan(cohortForm);
      setFeedback(`Angkatan ${created.tahun_masuk} berhasil ditambahkan.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menambah angkatan.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteCohort = async (cohort) => {
    setError('');
    setFeedback('');
    setBusyKey(cohort.id);
    try {
      await deleteAngkatan(cohort.id);
      setFeedback(`Angkatan ${cohort.tahun_masuk} dihapus.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menghapus angkatan.');
    } finally {
      setBusyKey('');
    }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    if (!selectedPeriodId) return;
    setError('');
    setFeedback('');
    setBusyKey('create-class');
    try {
      const created = await createKelasPeriode(selectedPeriodId, classForm);
      setFeedback(`Kelas ${created.label} berhasil dibuat.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menambah kelas.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteClass = async (klass) => {
    setError('');
    setFeedback('');
    setBusyKey(klass.id);
    try {
      await deleteKelasPeriode(selectedPeriodId, klass.id);
      setFeedback(`Kelas ${klass.label} dihapus.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menghapus kelas.');
    } finally {
      setBusyKey('');
    }
  };

  const handleLinkStudent = async (e) => {
    e.preventDefault();
    if (!selectedCohortId || !linkUserId.trim()) return;
    setError('');
    setFeedback('');
    setBusyKey('link-student');
    try {
      const linked = await linkAngkatanMahasiswa(
        selectedCohortId,
        linkUserId.trim(),
      );
      setLinkUserId('');
      setFeedback(
        `Mahasiswa ${linked.nama} (${linked.nim_nidn}) ditautkan ke angkatan.`,
      );
      await handleCohortChange(selectedCohortId);
    } catch (err) {
      setError(err.message || 'Gagal menautkan mahasiswa.');
    } finally {
      setBusyKey('');
    }
  };

  const handleCreateRoster = async (e) => {
    e.preventDefault();
    if (!selectedPeriodId) return;
    setError('');
    setFeedback('');
    setBusyKey('create-roster');
    try {
      await createRoster(selectedPeriodId, rosterForm);
      setRosterForm((prev) => ({ ...prev, mahasiswa_id: '' }));
      setFeedback('Mahasiswa berhasil ditempatkan pada roster periode.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menempatkan mahasiswa.');
    } finally {
      setBusyKey('');
    }
  };

  const handleRosterStatus = async (entry, nextStatus) => {
    setError('');
    setFeedback('');
    setBusyKey(entry.id);
    try {
      await updateRoster(selectedPeriodId, entry.mahasiswa_id, {
        status: nextStatus,
      });
      setFeedback('Status mahasiswa pada periode diperbarui.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal memperbarui status roster.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteRoster = async (entry) => {
    setError('');
    setFeedback('');
    setBusyKey(entry.id);
    try {
      await deleteRoster(selectedPeriodId, entry.mahasiswa_id);
      setFeedback('Mahasiswa dihapus dari roster periode.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menghapus entri roster.');
    } finally {
      setBusyKey('');
    }
  };

  const cohortById = Object.fromEntries(cohorts.map((c) => [c.id, c]));
  const classById = Object.fromEntries(classes.map((k) => [k.id, k]));
  const studentById = Object.fromEntries(students.map((s) => [s.id, s]));

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
          Angkatan & Roster
        </h1>
        <p className="text-[14px] text-[#566B70] mt-2">
          Kelola angkatan beserta versi kurikulumnya, kelas reguler A–E (semester
          1–8), kelas K untuk Cuti/Nonaktif, dan roster periode.
        </p>
      </div>

      <LockedPeriodBanner period={selectedPeriod} />

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#F7EAE1] border border-[#E8B899] px-4 py-3 text-[13px] text-[#9A4213]"
        >
          {error}
        </div>
      )}

      {feedback && (
        <div className="rounded-[10px] bg-[#E6F2EE] border border-[#B8DCD0] px-4 py-3 text-[13px] text-[#1A5C4D]">
          {feedback}
        </div>
      )}

      {/* Bagian 1: Angkatan */}
      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
        <h2 className="text-[17px] font-semibold text-[#15333A]">
          Angkatan &amp; Versi Kurikulum
        </h2>

        <form
          onSubmit={handleCreateCohort}
          className="grid grid-cols-[180px_1fr_auto] gap-3 items-end"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-[#334B51]">
              Tahun masuk
            </label>
            <input
              type="number"
              required
              min={1900}
              max={9998}
              value={cohortForm.tahun_masuk}
              onChange={(e) =>
                setCohortForm((prev) => ({
                  ...prev,
                  tahun_masuk: e.target.value,
                }))
              }
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-[#334B51]">
              Kurikulum Aktif
            </label>
            <select
              required
              value={cohortForm.kurikulum_id}
              onChange={(e) =>
                setCohortForm((prev) => ({
                  ...prev,
                  kurikulum_id: e.target.value,
                }))
              }
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            >
              {activeCurricula.length === 0 ? (
                <option value="">Belum ada kurikulum Aktif</option>
              ) : (
                activeCurricula.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nama} ({c.kode_kurikulum})
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            type="submit"
            disabled={busyKey === 'create-cohort' || activeCurricula.length === 0}
            className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer disabled:opacity-50"
          >
            + Tambah Angkatan
          </button>
        </form>

        <div className="divide-y divide-[#EFECE4]">
          {loading ? (
            <p className="py-4 text-[13px] text-[#566B70]">
              Memuat angkatan...
            </p>
          ) : cohorts.length === 0 ? (
            <p className="py-4 text-[13px] text-[#566B70]">
              Belum ada angkatan.
            </p>
          ) : (
            cohorts.map((cohort) => (
              <div
                key={cohort.id}
                className="py-3 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <span className="text-[14px] font-semibold">
                    Angkatan {cohort.tahun_masuk}
                  </span>
                  <span className="text-[12.5px] text-[#566B70]">
                    {curriculumById[cohort.kurikulum_id]?.nama ||
                      cohort.kurikulum_id}
                  </span>
                </div>
                <button
                  type="button"
                  disabled={busyKey === cohort.id}
                  onClick={() => handleDeleteCohort(cohort)}
                  className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] text-[#B55824] cursor-pointer"
                >
                  Hapus
                </button>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Bagian 2: Kelas Periode */}
      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
        <div>
          <h2 className="text-[17px] font-semibold text-[#15333A]">
            Kelas pada Periode Terpilih
          </h2>
          <p className="text-[12px] text-[#566B70] mt-1">
            {selectedPeriod
              ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester} (${selectedPeriod.status})`
              : 'Pilih periode akademik di topbar terlebih dahulu.'}
          </p>
        </div>

        {selectedPeriod && (
          <>
            <form
              onSubmit={handleCreateClass}
              className="grid grid-cols-[1fr_140px_160px_auto] gap-3 items-end"
            >
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Angkatan
                </label>
                <select
                  required
                  value={classForm.angkatan_id}
                  onChange={(e) =>
                    setClassForm((prev) => ({
                      ...prev,
                      angkatan_id: e.target.value,
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                >
                  {cohorts.map((c) => (
                    <option key={c.id} value={c.id}>
                      Angkatan {c.tahun_masuk}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Huruf kelas
                </label>
                <select
                  value={classForm.kode_kelas}
                  onChange={(e) => {
                    const nextKode = e.target.value;
                    setClassForm((prev) => ({
                      ...prev,
                      kode_kelas: nextKode,
                      semester_studi:
                        nextKode === 'K' ? '' : prev.semester_studi || 1,
                    }));
                  }}
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                >
                  {KODE_KELAS_OPTIONS.map((k) => (
                    <option key={k} value={k}>
                      Kelas {k}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Semester studi
                </label>
                <select
                  disabled={classForm.kode_kelas === 'K'}
                  value={
                    classForm.kode_kelas === 'K' ? '' : classForm.semester_studi
                  }
                  onChange={(e) =>
                    setClassForm((prev) => ({
                      ...prev,
                      semester_studi: Number(e.target.value),
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] disabled:opacity-50"
                >
                  {classForm.kode_kelas === 'K' ? (
                    <option value="">Kosong (Cuti/Nonaktif)</option>
                  ) : (
                    [1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>
                        Semester {s}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <button
                type="submit"
                disabled={busyKey === 'create-class' || cohorts.length === 0}
                className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
              >
                + Tambah Kelas
              </button>
            </form>

            <div className="divide-y divide-[#EFECE4]">
              {classes.length === 0 ? (
                <p className="py-4 text-[13px] text-[#566B70]">
                  Belum ada kelas pada periode ini.
                </p>
              ) : (
                classes.map((klass) => (
                  <div
                    key={klass.id}
                    className="py-3 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-[14px] font-semibold">
                        {klass.label}
                      </span>
                      <span className="text-[12.5px] text-[#566B70]">
                        Angkatan{' '}
                        {cohortById[klass.angkatan_id]?.tahun_masuk ?? '—'} ·{' '}
                        {klass.kode_kelas === 'K'
                          ? 'Kelas K (Cuti / Nonaktif)'
                          : `Semester ${klass.semester_studi}`}
                      </span>
                    </div>
                    <button
                      type="button"
                      disabled={busyKey === klass.id}
                      onClick={() => handleDeleteClass(klass)}
                      className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] text-[#B55824] cursor-pointer"
                    >
                      Hapus
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </section>

      {/* Bagian 3: Mahasiswa & Roster Periode */}
      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#15333A]">
              Mahasiswa &amp; Roster Periode
            </h2>
            <p className="text-[12px] text-[#566B70] mt-1">
              Mahasiswa Aktif ditempatkan di kelas reguler A–E; status Cuti
              atau Nonaktif ditempatkan di kelas K.
            </p>
          </div>

          <select
            aria-label="Pilih angkatan mahasiswa"
            value={selectedCohortId}
            onChange={(e) => handleCohortChange(e.target.value)}
            className="h-[36px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
          >
            {cohorts.map((c) => (
              <option key={c.id} value={c.id}>
                Angkatan {c.tahun_masuk}
              </option>
            ))}
          </select>
        </div>

        <form
          onSubmit={handleLinkStudent}
          className="grid grid-cols-[1fr_auto] gap-3 items-end"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-[#334B51]">
              Tautkan User ID Mahasiswa ke Angkatan terpilih (daftar akun
              menunggu endpoint Pengguna)
            </label>
            <input
              type="text"
              value={linkUserId}
              onChange={(e) => setLinkUserId(e.target.value)}
              placeholder="UUID pengguna ber-role Mahasiswa"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>
          <button
            type="submit"
            disabled={busyKey === 'link-student' || !selectedCohortId}
            className="h-[38px] px-4 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium cursor-pointer"
          >
            Tautkan ke angkatan
          </button>
        </form>

        {selectedPeriod && (
          <form
            onSubmit={handleCreateRoster}
            className="grid grid-cols-[1fr_200px_140px_auto] gap-3 items-end pt-2 border-t border-[#E4DFD4]"
          >
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-[#334B51]">
                Mahasiswa angkatan ({students.length})
              </label>
              <select
                required
                value={rosterForm.mahasiswa_id}
                onChange={(e) =>
                  setRosterForm((prev) => ({
                    ...prev,
                    mahasiswa_id: e.target.value,
                  }))
                }
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              >
                <option value="">Pilih mahasiswa</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nim_nidn} · {s.nama}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-[#334B51]">
                Kelas periode
              </label>
              <select
                required
                value={rosterForm.kelas_periode_id}
                onChange={(e) => {
                  const kelas = classById[e.target.value];
                  setRosterForm((prev) => ({
                    ...prev,
                    kelas_periode_id: e.target.value,
                    status:
                      kelas?.kode_kelas === 'K'
                        ? prev.status === 'Aktif'
                          ? 'Cuti'
                          : prev.status
                        : 'Aktif',
                  }));
                }}
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              >
                <option value="">Pilih kelas</option>
                {classes.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label} (Angkatan{' '}
                    {cohortById[k.angkatan_id]?.tahun_masuk ?? '—'})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-[#334B51]">
                Status
              </label>
              <select
                value={rosterForm.status}
                onChange={(e) =>
                  setRosterForm((prev) => ({ ...prev, status: e.target.value }))
                }
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              >
                {STATUS_MAHASISWA_OPTIONS.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={busyKey === 'create-roster'}
              className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
            >
              + Tempatkan
            </button>
          </form>
        )}

        <div className="divide-y divide-[#EFECE4]">
          {roster.length === 0 ? (
            <p className="py-4 text-[13px] text-[#566B70]">
              Belum ada roster mahasiswa pada periode ini.
            </p>
          ) : (
            roster.map((entry) => {
              const student = studentById[entry.mahasiswa_id];
              const klass = classById[entry.kelas_periode_id];
              return (
                <div
                  key={entry.id}
                  className="py-3 flex items-center justify-between gap-4 text-[13px]"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-medium">
                      {student
                        ? `${student.nim_nidn} · ${student.nama}`
                        : entry.mahasiswa_id}
                    </span>
                    <span className="text-[#566B70]">
                      Kelas: {klass?.label || entry.kelas_periode_id}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      aria-label="Ubah status roster"
                      value={entry.status}
                      disabled={busyKey === entry.id}
                      onChange={(e) => handleRosterStatus(entry, e.target.value)}
                      className="h-[30px] px-2 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12px]"
                    >
                      {STATUS_MAHASISWA_OPTIONS.map((st) => (
                        <option key={st} value={st}>
                          {st}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={busyKey === entry.id}
                      onClick={() => handleDeleteRoster(entry)}
                      className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] text-[#B55824] cursor-pointer"
                    >
                      Keluarkan
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
