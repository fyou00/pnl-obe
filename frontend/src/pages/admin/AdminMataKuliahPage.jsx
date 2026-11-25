import { useCallback, useEffect, useState } from 'react';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  createMataKuliah,
  createPaketMk,
  deleteMataKuliah,
  deletePaketMk,
  listMataKuliah,
  listPaketMk,
  updateMataKuliah,
  updatePaketMk,
} from '../../lib/adminApi.js';

export default function AdminMataKuliahPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedCurriculum,
  } = useAdminWorkspace();

  const [tab, setTab] = useState('paket');
  const [masterList, setMasterList] = useState([]);
  const [paketList, setPaketList] = useState([]);
  const [semesterFilter, setSemesterFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyId, setBusyId] = useState('');

  const [masterForm, setMasterForm] = useState({
    kode_mk: '',
    nama_mk: '',
    deskripsi: '',
    aktif: true,
  });
  const [editingMasterId, setEditingMasterId] = useState('');
  const [editMasterForm, setEditMasterForm] = useState({
    kode_mk: '',
    nama_mk: '',
    deskripsi: '',
    aktif: true,
  });

  const [paketForm, setPaketForm] = useState({
    mk_id: '',
    nama_mk: '',
    sks: 3,
    semester: 1,
    deskripsi: '',
  });
  const [editingPaketId, setEditingPaketId] = useState('');
  const [editPaketForm, setEditPaketForm] = useState({
    nama_mk: '',
    sks: 3,
    semester: 1,
    deskripsi: '',
  });

  const isDraft = selectedCurriculum?.status === 'Draft';

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [masters, pakets] = await Promise.all([
        listMataKuliah({ limit: 100 }),
        selectedCurriculumId
          ? listPaketMk(selectedCurriculumId, {
              limit: 100,
              semester: semesterFilter ? Number(semesterFilter) : undefined,
            })
          : Promise.resolve([]),
      ]);
      setMasterList(masters);
      setPaketList(pakets);
    } catch (err) {
      setError(err.message || 'Gagal memuat data mata kuliah.');
    } finally {
      setLoading(false);
    }
  }, [selectedCurriculumId, semesterFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMasterCreate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId('master-create');
    try {
      await createMataKuliah({
        ...masterForm,
        deskripsi: masterForm.deskripsi.trim() || null,
      });
      setMasterForm({ kode_mk: '', nama_mk: '', deskripsi: '', aktif: true });
      setFeedback('Master mata kuliah berhasil ditambahkan.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal membuat master mata kuliah.');
    } finally {
      setBusyId('');
    }
  };

  const handleMasterUpdate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId(editingMasterId);
    try {
      await updateMataKuliah(editingMasterId, {
        ...editMasterForm,
        deskripsi: editMasterForm.deskripsi.trim() || null,
      });
      setEditingMasterId('');
      setFeedback('Master mata kuliah diperbarui.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal memperbarui master mata kuliah.');
    } finally {
      setBusyId('');
    }
  };

  const handleMasterDelete = async (mk) => {
    setError('');
    setFeedback('');
    setBusyId(mk.id);
    try {
      await deleteMataKuliah(mk.id);
      setFeedback(`Master MK ${mk.kode_mk} dihapus.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menghapus master mata kuliah.');
    } finally {
      setBusyId('');
    }
  };

  const handlePickMaster = (mkId) => {
    const found = masterList.find((m) => m.id === mkId);
    setPaketForm((prev) => ({
      ...prev,
      mk_id: mkId,
      nama_mk: found ? found.nama_mk : prev.nama_mk,
      deskripsi: found?.deskripsi || '',
    }));
  };

  const handlePaketCreate = async (e) => {
    e.preventDefault();
    if (!selectedCurriculumId) return;
    setError('');
    setFeedback('');
    setBusyId('paket-create');
    try {
      await createPaketMk(selectedCurriculumId, {
        ...paketForm,
        deskripsi: paketForm.deskripsi.trim() || null,
      });
      setPaketForm({
        mk_id: '',
        nama_mk: '',
        sks: 3,
        semester: 1,
        deskripsi: '',
      });
      setFeedback('Mata kuliah ditambahkan ke paket kurikulum Draft.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menambahkan MK ke kurikulum.');
    } finally {
      setBusyId('');
    }
  };

  const handlePaketUpdate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId(editingPaketId);
    try {
      await updatePaketMk(selectedCurriculumId, editingPaketId, {
        ...editPaketForm,
        deskripsi: editPaketForm.deskripsi.trim() || null,
      });
      setEditingPaketId('');
      setFeedback('Paket mata kuliah kurikulum diperbarui.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal memperbarui paket MK.');
    } finally {
      setBusyId('');
    }
  };

  const handlePaketDelete = async (item) => {
    setError('');
    setFeedback('');
    setBusyId(item.id);
    try {
      await deletePaketMk(selectedCurriculumId, item.id);
      setFeedback(`${item.nama_mk} dihapus dari paket kurikulum.`);
      await loadData();
    } catch (err) {
      setError(err.message || 'Gagal menghapus MK dari paket kurikulum.');
    } finally {
      setBusyId('');
    }
  };

  const masterById = Object.fromEntries(masterList.map((m) => [m.id, m]));

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Mata kuliah
          </h1>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
            Kelola identitas Master Mata Kuliah dan snapshot paket MK per
            semester pada versi kurikulum.
          </p>
        </div>

        <select
          aria-label="Pilih versi kurikulum"
          value={selectedCurriculumId}
          onChange={(e) => setSelectedCurriculumId(e.target.value)}
          disabled={curricula.length === 0}
          className="min-w-[218px] h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[12px] font-medium"
        >
          {curricula.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nama} ({item.status})
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setTab('paket')}
          className={[
            'h-[36px] px-4 rounded-[7px] text-[12.5px] font-medium cursor-pointer',
            tab === 'paket'
              ? 'bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525]'
              : 'bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[#525252] dark:text-[#A3A3A0]',
          ].join(' ')}
        >
          Paket MK Kurikulum
        </button>
        <button
          type="button"
          onClick={() => setTab('master')}
          className={[
            'h-[36px] px-4 rounded-[7px] text-[12.5px] font-medium cursor-pointer',
            tab === 'master'
              ? 'bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525]'
              : 'bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[#525252] dark:text-[#A3A3A0]',
          ].join(' ')}
        >
          Master Mata Kuliah ({masterList.length})
        </button>
      </div>

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

      {tab === 'paket' ? (
        <>
          {selectedCurriculum && !isDraft && (
            <div className="rounded-[10px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] px-4 py-3 text-[13px] text-[#525252] dark:text-[#D4D4D0]">
              Kurikulum <strong>{selectedCurriculum.nama}</strong> berstatus{' '}
              <strong>{selectedCurriculum.status}</strong> (read-only).
            </div>
          )}

          {isDraft && (
            <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
              <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                Tambah MK ke Paket Kurikulum
              </h2>
              <form
                onSubmit={handlePaketCreate}
                className="mt-4 grid grid-cols-[260px_1fr_90px_110px_auto] gap-3 items-end"
              >
                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                    Master MK
                  </label>
                  <select
                    required
                    value={paketForm.mk_id}
                    onChange={(e) => handlePickMaster(e.target.value)}
                    className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                  >
                    <option value="">Pilih Master MK</option>
                    {masterList
                      .filter((m) => m.aktif)
                      .map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.kode_mk} · {m.nama_mk}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                    Nama MK pada versi kurikulum
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={100}
                    value={paketForm.nama_mk}
                    onChange={(e) =>
                      setPaketForm((prev) => ({
                        ...prev,
                        nama_mk: e.target.value,
                      }))
                    }
                    className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                    SKS
                  </label>
                  <input
                    type="number"
                    required
                    min={1}
                    max={20}
                    value={paketForm.sks}
                    onChange={(e) =>
                      setPaketForm((prev) => ({ ...prev, sks: e.target.value }))
                    }
                    className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                    Semester
                  </label>
                  <select
                    value={paketForm.semester}
                    onChange={(e) =>
                      setPaketForm((prev) => ({
                        ...prev,
                        semester: Number(e.target.value),
                      }))
                    }
                    className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>
                        Semester {s}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={busyId === 'paket-create'}
                  className="h-[38px] px-4 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                >
                  + Tambah
                </button>
              </form>
            </section>
          )}

          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                Daftar Paket MK ({paketList.length})
              </h2>

              <select
                aria-label="Filter semester"
                value={semesterFilter}
                onChange={(e) => setSemesterFilter(e.target.value)}
                className="h-[36px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[12px]"
              >
                <option value="">Semua semester (1–8)</option>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            {loading ? (
              <p className="py-6 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                Memuat paket mata kuliah...
              </p>
            ) : paketList.length === 0 ? (
              <p className="py-6 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                Belum ada mata kuliah dalam paket kurikulum ini.
              </p>
            ) : (
              <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
                {paketList.map((item) => {
                  const master = masterById[item.mk_id];
                  const isEditing = editingPaketId === item.id;
                  return (
                    <div key={item.id} className="py-3.5">
                      {isEditing ? (
                        <form
                          onSubmit={handlePaketUpdate}
                          className="grid grid-cols-[1fr_90px_110px_auto_auto] gap-3 items-center"
                        >
                          <input
                            type="text"
                            required
                            maxLength={100}
                            value={editPaketForm.nama_mk}
                            onChange={(e) =>
                              setEditPaketForm((prev) => ({
                                ...prev,
                                nama_mk: e.target.value,
                              }))
                            }
                            className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                          />
                          <input
                            type="number"
                            required
                            min={1}
                            max={20}
                            value={editPaketForm.sks}
                            onChange={(e) =>
                              setEditPaketForm((prev) => ({
                                ...prev,
                                sks: e.target.value,
                              }))
                            }
                            className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                          />
                          <select
                            value={editPaketForm.semester}
                            onChange={(e) =>
                              setEditPaketForm((prev) => ({
                                ...prev,
                                semester: Number(e.target.value),
                              }))
                            }
                            className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                          >
                            {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                              <option key={s} value={s}>
                                Smt {s}
                              </option>
                            ))}
                          </select>
                          <button
                            type="submit"
                            disabled={busyId === item.id}
                            className="h-[34px] px-3 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                          >
                            Simpan
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingPaketId('')}
                            className="h-[34px] px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                          >
                            Batal
                          </button>
                        </form>
                      ) : (
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex items-center gap-4 min-w-0">
                            <span className="w-[100px] text-[12.5px] font-semibold text-[#525252] dark:text-[#A3A3A0] shrink-0">
                              {master?.kode_mk || '—'}
                            </span>
                            <span className="text-[13.5px] font-medium text-[#252525] dark:text-[#F5F5F4] truncate">
                              {item.nama_mk}
                            </span>
                            <span className="text-[12px] text-[#737373] dark:text-[#A3A3A0] shrink-0">
                              Semester {item.semester} · {item.sks} SKS
                            </span>
                          </div>

                          {isDraft && (
                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingPaketId(item.id);
                                  setEditPaketForm({
                                    nama_mk: item.nama_mk,
                                    sks: item.sks,
                                    semester: item.semester,
                                    deskripsi: item.deskripsi || '',
                                  });
                                }}
                                className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                              >
                                Ubah
                              </button>
                              <button
                                type="button"
                                disabled={busyId === item.id}
                                onClick={() => handlePaketDelete(item)}
                                className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] text-[#B55824] cursor-pointer"
                              >
                                Hapus
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </>
      ) : (
        <>
          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
              Tambah Master Mata Kuliah
            </h2>
            <form
              onSubmit={handleMasterCreate}
              className="mt-4 grid grid-cols-[160px_1fr_1fr_auto] gap-3 items-end"
            >
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                  Kode MK
                </label>
                <input
                  type="text"
                  required
                  maxLength={20}
                  value={masterForm.kode_mk}
                  onChange={(e) =>
                    setMasterForm((prev) => ({
                      ...prev,
                      kode_mk: e.target.value,
                    }))
                  }
                  placeholder="TIK501"
                  className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                  Nama Mata Kuliah
                </label>
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={masterForm.nama_mk}
                  onChange={(e) =>
                    setMasterForm((prev) => ({
                      ...prev,
                      nama_mk: e.target.value,
                    }))
                  }
                  placeholder="Basis Data"
                  className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
                  Deskripsi (opsional)
                </label>
                <input
                  type="text"
                  value={masterForm.deskripsi}
                  onChange={(e) =>
                    setMasterForm((prev) => ({
                      ...prev,
                      deskripsi: e.target.value,
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                />
              </div>
              <button
                type="submit"
                disabled={busyId === 'master-create'}
                className="h-[38px] px-4 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
              >
                + Tambah Master MK
              </button>
            </form>
          </section>

          <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
            <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4] mb-4">
              Daftar Master Mata Kuliah
            </h2>
            <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
              {masterList.map((mk) => {
                const isEditing = editingMasterId === mk.id;
                return (
                  <div key={mk.id} className="py-3.5">
                    {isEditing ? (
                      <form
                        onSubmit={handleMasterUpdate}
                        className="grid grid-cols-[140px_1fr_auto_auto_auto] gap-3 items-center"
                      >
                        <input
                          type="text"
                          required
                          maxLength={20}
                          value={editMasterForm.kode_mk}
                          onChange={(e) =>
                            setEditMasterForm((prev) => ({
                              ...prev,
                              kode_mk: e.target.value,
                            }))
                          }
                          className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                        />
                        <input
                          type="text"
                          required
                          maxLength={100}
                          value={editMasterForm.nama_mk}
                          onChange={(e) =>
                            setEditMasterForm((prev) => ({
                              ...prev,
                              nama_mk: e.target.value,
                            }))
                          }
                          className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                        />
                        <label className="text-[12px] inline-flex items-center gap-1.5">
                          <input
                            type="checkbox"
                            checked={editMasterForm.aktif}
                            onChange={(e) =>
                              setEditMasterForm((prev) => ({
                                ...prev,
                                aktif: e.target.checked,
                              }))
                            }
                          />
                          <span>Aktif</span>
                        </label>
                        <button
                          type="submit"
                          disabled={busyId === mk.id}
                          className="h-[34px] px-3 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                        >
                          Simpan
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingMasterId('')}
                          className="h-[34px] px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                        >
                          Batal
                        </button>
                      </form>
                    ) : (
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                          <span className="w-[100px] text-[12.5px] font-semibold">
                            {mk.kode_mk}
                          </span>
                          <span className="text-[13.5px]">{mk.nama_mk}</span>
                          <span className="px-2 py-0.5 rounded bg-[#F0F0EF] dark:bg-[#2A2A27] text-[11px]">
                            {mk.aktif ? 'Aktif' : 'Nonaktif'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingMasterId(mk.id);
                              setEditMasterForm({
                                kode_mk: mk.kode_mk,
                                nama_mk: mk.nama_mk,
                                deskripsi: mk.deskripsi || '',
                                aktif: mk.aktif,
                              });
                            }}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                          >
                            Ubah
                          </button>
                          <button
                            type="button"
                            disabled={busyId === mk.id}
                            onClick={() => handleMasterDelete(mk)}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] text-[#B55824] cursor-pointer"
                          >
                            Hapus
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
