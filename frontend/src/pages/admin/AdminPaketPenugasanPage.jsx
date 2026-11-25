import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { LockedPeriodBanner } from '../../components/states/SystemStates.jsx';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  applyPaket,
  changePengampu,
  getPaketPreview,
  listAngkatan,
  listDosen,
} from '../../lib/adminApi.js';

export default function AdminPaketPenugasanPage() {
  const { selectedPeriodId, selectedPeriod } = useAdminWorkspace();

  const [cohorts, setCohorts] = useState([]);
  const [selectedAngkatanId, setSelectedAngkatanId] = useState('');
  const [lecturers, setLecturers] = useState([]);
  const [preview, setPreview] = useState(null);
  const [assignments, setAssignments] = useState({});

  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  const [previewNote, setPreviewNote] = useState('');
  const [result, setResult] = useState(null);

  const loadMeta = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [cohortsData, lecturersData] = await Promise.all([
        listAngkatan({ limit: 100 }),
        listDosen({ limit: 100, aktif: true }),
      ]);
      setCohorts(cohortsData);
      setLecturers(lecturersData);
      setSelectedAngkatanId((prev) =>
        prev && cohortsData.some((c) => c.id === prev)
          ? prev
          : cohortsData[0]?.id || '',
      );
    } catch (err) {
      setError(err.message || 'Gagal memuat daftar angkatan dan dosen.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  const loadPreview = useCallback(async () => {
    if (!selectedPeriodId || !selectedAngkatanId) {
      setPreview(null);
      return;
    }
    setLoading(true);
    setPreviewNote('');
    setResult(null);
    try {
      const data = await getPaketPreview(selectedPeriodId, selectedAngkatanId);
      setPreview(data);
      const map = {};
      for (const pair of data.penugasan) {
        map[`${pair.kelas_periode_id}:${pair.kurikulum_mk_id}`] =
          pair.dosen_id || '';
      }
      setAssignments(map);
    } catch (err) {
      setPreview(null);
      setPreviewNote(err.message || 'Pratinjau paket belum tersedia.');
    } finally {
      setLoading(false);
    }
  }, [selectedAngkatanId, selectedPeriodId]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  const setPairLecturer = (kelasId, mkId, dosenId) => {
    setAssignments((prev) => ({
      ...prev,
      [`${kelasId}:${mkId}`]: dosenId,
    }));
  };

  const assignCourseToAllClasses = (mkId, dosenId) => {
    if (!preview || !dosenId) return;
    setAssignments((prev) => {
      const next = { ...prev };
      for (const klass of preview.kelas) {
        next[`${klass.kelas_periode_id}:${mkId}`] = dosenId;
      }
      return next;
    });
  };

  const handleApplyPackage = async () => {
    if (!preview) return;
    const payload = preview.penugasan.map((pair) => ({
      kelas_periode_id: pair.kelas_periode_id,
      kurikulum_mk_id: pair.kurikulum_mk_id,
      dosen_id:
        assignments[`${pair.kelas_periode_id}:${pair.kurikulum_mk_id}`] || '',
    }));

    if (payload.some((item) => !item.dosen_id)) {
      setError('Tetapkan tepat satu dosen untuk setiap pasangan kelas MK.');
      return;
    }

    setError('');
    setApplying(true);
    try {
      const res = await applyPaket(
        selectedPeriodId,
        selectedAngkatanId,
        payload,
      );
      setResult(res);
      await loadPreview();
    } catch (err) {
      setError(err.message || 'Gagal menerapkan paket.');
    } finally {
      setApplying(false);
    }
  };

  const handleUpdateSingleLecturer = async (pair) => {
    const key = `${pair.kelas_periode_id}:${pair.kurikulum_mk_id}`;
    const dosenId = assignments[key];
    if (!pair.kelas_mk_id || !dosenId) return;
    setError('');
    setApplying(true);
    try {
      await changePengampu(pair.kelas_mk_id, dosenId);
      await loadPreview();
    } catch (err) {
      setError(err.message || 'Gagal mengganti pengampu.');
    } finally {
      setApplying(false);
    }
  };

  const pairLookup = Object.fromEntries(
    (preview?.penugasan || []).map((p) => [
      `${p.kelas_periode_id}:${p.kurikulum_mk_id}`,
      p,
    ]),
  );

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Paket & Penugasan
          </h1>
          <p className="text-[14px] text-[#566B70] mt-2">
            Terapkan paket MK semester studi ke seluruh kelas reguler angkatan
            dan tetapkan satu dosen per kelas MK.
          </p>
        </div>

        <select
          aria-label="Pilih angkatan"
          value={selectedAngkatanId}
          onChange={(e) => setSelectedAngkatanId(e.target.value)}
          disabled={cohorts.length === 0}
          className="min-w-[200px] h-[38px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[12px] font-medium"
        >
          {cohorts.length === 0 ? (
            <option value="">Belum ada angkatan</option>
          ) : (
            cohorts.map((c) => (
              <option key={c.id} value={c.id}>
                Angkatan {c.tahun_masuk}
              </option>
            ))
          )}
        </select>
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

      {result && (
        <div className="rounded-[10px] bg-[#E6F2EE] border border-[#B8DCD0] px-4 py-3 text-[13px] text-[#1A5C4D]">
          Paket semester {result.semester_studi} diterapkan:{' '}
          <strong>{result.total_kelas_mk}</strong> kelas MK,{' '}
          <strong>{result.total_peserta}</strong> peserta aktif (dibuat:{' '}
          {result.kelas_mk_dibuat}, diperbarui: {result.kelas_mk_diperbarui},
          rancangan bersama baru: {result.rancangan_dibuat}, peserta ditambah:{' '}
          {result.peserta_ditambahkan}).
        </div>
      )}

      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
        {loading ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Memuat pratinjau paket...
          </p>
        ) : !selectedPeriod ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Pilih periode akademik pada topbar terlebih dahulu.
          </p>
        ) : previewNote ? (
          <div className="flex flex-col gap-3 py-4">
            <p className="text-[14px] font-medium text-[#B55824]">
              {previewNote}
            </p>
            <p className="text-[12.5px] text-[#566B70]">
              Pastikan kurikulum angkatan berstatus Aktif, kelas reguler A–E
              sudah dibuat untuk periode{' '}
              {selectedPeriod.tahun_akademik} {selectedPeriod.semester}, paket MK
              semester studi tersedia, dan setiap MK sudah dibebankan CPL.
            </p>
            <div className="flex items-center gap-4 text-[12.5px] font-medium">
              <Link to="/admin/kurikulum" className="underline">
                Versi kurikulum →
              </Link>
              <Link to="/admin/matriks" className="underline">
                Matriks pembebanan →
              </Link>
              <Link to="/admin/angkatan" className="underline">
                Angkatan dan kelas →
              </Link>
            </div>
          </div>
        ) : !preview ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Pilih angkatan untuk melihat pratinjau paket.
          </p>
        ) : (
          <>
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-[17px] font-semibold text-[#15333A]">
                  Matriks Penugasan · Semester {preview.semester_studi}
                </h2>
                <p className="text-[12px] text-[#566B70] mt-1">
                  {preview.kelas.length} kelas reguler ·{' '}
                  {preview.mata_kuliah.length} mata kuliah paket · Dosen sama
                  pada MK yang sama otomatis memakai satu rancangan bersama.
                </p>
              </div>

              <button
                type="button"
                disabled={applying || selectedPeriod.status !== 'Dibuka'}
                onClick={handleApplyPackage}
                className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer disabled:opacity-50 shrink-0"
              >
                {applying ? 'Menerapkan...' : 'Terapkan Paket Massal'}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E4DFD4] text-[11px] font-medium text-[#566B70]">
                    <th className="py-3 pr-4 min-w-[230px]">Mata kuliah</th>
                    <th className="py-3 pr-4 min-w-[170px]">
                      Set semua kelas
                    </th>
                    {preview.kelas.map((klass) => (
                      <th key={klass.kelas_periode_id} className="py-3 px-2 min-w-[185px]">
                        <div className="text-[#15333A] font-semibold">
                          {klass.label}
                        </div>
                        <div className="text-[10.5px]">
                          {klass.jumlah_mahasiswa_aktif} aktif
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFECE4]">
                  {preview.mata_kuliah.map((course) => (
                    <tr key={course.kurikulum_mk_id}>
                      <td className="py-3.5 pr-4 align-top">
                        <div className="text-[13px] font-medium text-[#15333A]">
                          {course.nama_mk}
                        </div>
                        <div className="text-[11px] text-[#566B70]">
                          {course.kode_mk} · {course.sks} SKS
                        </div>
                      </td>
                      <td className="py-3.5 pr-4 align-top">
                        <select
                          aria-label={`Set dosen semua kelas ${course.nama_mk}`}
                          defaultValue=""
                          onChange={(e) => {
                            if (e.target.value) {
                              assignCourseToAllClasses(
                                course.kurikulum_mk_id,
                                e.target.value,
                              );
                            }
                          }}
                          className="w-full h-[34px] px-2 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
                        >
                          <option value="">Isi cepat...</option>
                          {lecturers.map((lecturer) => (
                            <option key={lecturer.id} value={lecturer.id}>
                              {lecturer.nama}
                            </option>
                          ))}
                        </select>
                      </td>
                      {preview.kelas.map((klass) => {
                        const key = `${klass.kelas_periode_id}:${course.kurikulum_mk_id}`;
                        const pair = pairLookup[key];
                        const currentDosenId = assignments[key] || '';
                        const hasChangedExisting =
                          pair?.kelas_mk_id &&
                          currentDosenId &&
                          currentDosenId !== pair.dosen_id;

                        return (
                          <td key={key} className="py-3.5 px-2 align-top">
                            <div className="flex flex-col gap-1.5">
                              <select
                                aria-label={`Dosen ${course.nama_mk} ${klass.label}`}
                                value={currentDosenId}
                                onChange={(e) =>
                                  setPairLecturer(
                                    klass.kelas_periode_id,
                                    course.kurikulum_mk_id,
                                    e.target.value,
                                  )
                                }
                                className="w-full h-[34px] px-2 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
                              >
                                <option value="">Pilih dosen...</option>
                                {lecturers.map((lecturer) => (
                                  <option key={lecturer.id} value={lecturer.id}>
                                    {lecturer.nama}
                                  </option>
                                ))}
                              </select>
                              {hasChangedExisting && (
                                <button
                                  type="button"
                                  disabled={applying}
                                  onClick={() => handleUpdateSingleLecturer(pair)}
                                  className="text-left text-[11px] font-medium text-[#15333A] underline cursor-pointer"
                                >
                                  Simpan ganti pengampu
                                </button>
                              )}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
