import { useCallback, useEffect, useMemo, useState } from 'react';
import ProfilLulusanOverview from '../../components/dashboard/ProfilLulusanOverview.jsx';
import { LoadingSkeleton } from '../../components/states/SystemStates.jsx';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  createProfilLulusan,
  deleteProfilLulusan,
  getProfilLulusanRingkasan,
  replacePlMatrix,
  updateProfilLulusan,
} from '../../lib/adminApi.js';

function setsEqual(leftIds, rightIds) {
  const left = new Set(leftIds || []);
  const right = new Set(rightIds || []);
  if (left.size !== right.size) return false;
  for (const item of left) {
    if (!right.has(item)) return false;
  }
  return true;
}

export default function AdminProfilLulusanPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedCurriculum,
  } = useAdminWorkspace();

  const [overview, setOverview] = useState(null);
  const [activeTab, setActiveTab] = useState('daftar');
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState('');
  const [savingMatrix, setSavingMatrix] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const [createForm, setCreateForm] = useState({
    kode_pl: '',
    nama_pl: '',
    bidang_kerja: '',
    deskripsi: '',
  });
  const [editingId, setEditingId] = useState('');
  const [editForm, setEditForm] = useState({
    kode_pl: '',
    nama_pl: '',
    bidang_kerja: '',
    deskripsi: '',
  });
  const [draftMatrix, setDraftMatrix] = useState({});

  const isDraft = selectedCurriculum?.status === 'Draft';

  const loadOverview = useCallback(async () => {
    if (!selectedCurriculumId) {
      setOverview(null);
      setDraftMatrix({});
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getProfilLulusanRingkasan({
        kurikulum_id: selectedCurriculumId,
      });
      setOverview(data);
      const nextDraft = {};
      for (const pl of data.profil_lulusan || []) {
        nextDraft[pl.id] = [...(pl.cpl_ids || [])];
      }
      setDraftMatrix(nextDraft);
    } catch (err) {
      setError(err.message || 'Gagal memuat Profil Lulusan kurikulum.');
      setOverview(null);
      setDraftMatrix({});
    } finally {
      setLoading(false);
    }
  }, [selectedCurriculumId]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const dirtyPlIds = useMemo(() => {
    if (!isDraft || !overview?.profil_lulusan) return [];
    return overview.profil_lulusan
      .filter((pl) => !setsEqual(draftMatrix[pl.id] || [], pl.cpl_ids || []))
      .map((pl) => pl.id);
  }, [draftMatrix, isDraft, overview]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!selectedCurriculumId || !isDraft) return;
    setError('');
    setFeedback('');
    setBusyId('create');
    try {
      await createProfilLulusan(selectedCurriculumId, {
        kode_pl: createForm.kode_pl.trim(),
        nama_pl: createForm.nama_pl.trim(),
        bidang_kerja: createForm.bidang_kerja.trim() || null,
        deskripsi: createForm.deskripsi.trim(),
      });
      setCreateForm({
        kode_pl: '',
        nama_pl: '',
        bidang_kerja: '',
        deskripsi: '',
      });
      setFeedback('Profil Lulusan baru berhasil ditambahkan ke kurikulum Draft.');
      await loadOverview();
    } catch (err) {
      setError(err.message || 'Gagal menambah Profil Lulusan.');
    } finally {
      setBusyId('');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!selectedCurriculumId || !editingId || !isDraft) return;
    setError('');
    setFeedback('');
    setBusyId(editingId);
    try {
      await updateProfilLulusan(selectedCurriculumId, editingId, {
        kode_pl: editForm.kode_pl.trim(),
        nama_pl: editForm.nama_pl.trim(),
        bidang_kerja: editForm.bidang_kerja.trim() || null,
        deskripsi: editForm.deskripsi.trim(),
      });
      setEditingId('');
      setFeedback('Profil Lulusan berhasil diperbarui.');
      await loadOverview();
    } catch (err) {
      setError(err.message || 'Gagal memperbarui Profil Lulusan.');
    } finally {
      setBusyId('');
    }
  };

  const handleDelete = async (pl) => {
    if (!selectedCurriculumId || !isDraft) return;
    setError('');
    setFeedback('');
    setBusyId(pl.id);
    try {
      await deleteProfilLulusan(selectedCurriculumId, pl.id);
      if (editingId === pl.id) setEditingId('');
      setFeedback(`Profil Lulusan ${pl.kode_pl} dihapus.`);
      await loadOverview();
    } catch (err) {
      setError(err.message || 'Gagal menghapus Profil Lulusan.');
    } finally {
      setBusyId('');
    }
  };

  const handleToggleMatrixLink = (plId, cplId) => {
    if (!isDraft) return;
    setFeedback('');
    setDraftMatrix((prev) => {
      const current = new Set(prev[plId] || []);
      if (current.has(cplId)) {
        current.delete(cplId);
      } else {
        current.add(cplId);
      }
      return { ...prev, [plId]: [...current] };
    });
  };

  const handleResetMatrix = () => {
    if (!overview?.profil_lulusan) return;
    const nextDraft = {};
    for (const pl of overview.profil_lulusan) {
      nextDraft[pl.id] = [...(pl.cpl_ids || [])];
    }
    setDraftMatrix(nextDraft);
    setError('');
    setFeedback('');
  };

  const handleSaveMatrix = async () => {
    if (!isDraft || !selectedCurriculumId || dirtyPlIds.length === 0) return;
    setError('');
    setFeedback('');
    setSavingMatrix(true);
    try {
      for (const plId of dirtyPlIds) {
        await replacePlMatrix(
          selectedCurriculumId,
          plId,
          draftMatrix[plId] || [],
        );
      }
      setFeedback('Matriks hubungan CPL–PL berhasil disimpan.');
      await loadOverview();
    } catch (err) {
      setError(err.message || 'Gagal menyimpan Matriks PL–CPL.');
    } finally {
      setSavingMatrix(false);
    }
  };

  const createSection = isDraft ? (
    <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6">
      <h2 className="text-[17px] font-semibold text-[#15333A]">
        Tambah Profil Lulusan
      </h2>
      <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-[160px_1fr_1fr] gap-4">
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="pl-create-kode"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Kode PL
            </label>
            <input
              id="pl-create-kode"
              type="text"
              required
              maxLength={10}
              value={createForm.kode_pl}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  kode_pl: e.target.value,
                }))
              }
              placeholder="PL-01"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="pl-create-nama"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Nama Profil Lulusan
            </label>
            <input
              id="pl-create-nama"
              type="text"
              required
              maxLength={150}
              value={createForm.nama_pl}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  nama_pl: e.target.value,
                }))
              }
              placeholder="Rekayasa Aplikasi (Application Engineer)"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="pl-create-bidang"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Bidang Kerja (pisahkan dengan koma)
            </label>
            <input
              id="pl-create-bidang"
              type="text"
              value={createForm.bidang_kerja}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  bidang_kerja: e.target.value,
                }))
              }
              placeholder="Web Developer, Backend Engineer, QA Engineer"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-end">
          <div className="flex-1 flex flex-col gap-1.5">
            <label
              htmlFor="pl-create-deskripsi"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Deskripsi Profil Lulusan
            </label>
            <textarea
              id="pl-create-deskripsi"
              required
              rows={2}
              value={createForm.deskripsi}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  deskripsi: e.target.value,
                }))
              }
              placeholder="Mampu merancang, mengembangkan, dan menguji perangkat lunak..."
              className="px-3 py-2 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <button
            type="submit"
            disabled={busyId === 'create'}
            className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12.5px] font-semibold cursor-pointer disabled:opacity-60 shrink-0"
          >
            {busyId === 'create' ? 'Menyimpan...' : '+ Tambah Profil Lulusan'}
          </button>
        </div>
      </form>
    </section>
  ) : null;

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Profil Lulusan &amp; Matriks PL–CPL
          </h1>
          <p className="text-[14px] text-[#566B70] mt-2">
            Tetapkan peran lulusan program studi dan pemetaan CPL pendukungnya.
            Perubahan hanya diizinkan pada kurikulum berstatus Draft.
          </p>
        </div>

        <select
          aria-label="Pilih versi kurikulum"
          value={selectedCurriculumId}
          onChange={(e) => {
            setSelectedCurriculumId(e.target.value);
            setEditingId('');
            setFeedback('');
          }}
          disabled={curricula.length === 0}
          className="min-w-[240px] h-[38px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[12px] font-medium"
        >
          {curricula.length === 0 ? (
            <option value="">Belum ada kurikulum</option>
          ) : (
            curricula.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nama} ({item.status})
              </option>
            ))
          )}
        </select>
      </div>

      {selectedCurriculum && !isDraft && (
        <div className="rounded-[10px] bg-white border border-[#E4DFD4] px-4 py-3 text-[13px] text-[#334B51]">
          Kurikulum <strong>{selectedCurriculum.nama}</strong> berstatus{' '}
          <strong>{selectedCurriculum.status}</strong> (read-only). Salin
          menjadi versi Draft di menu Versi Kurikulum bila perlu mengubah Profil
          Lulusan atau matriks PL–CPL.
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
        >
          {error}
        </div>
      )}

      {feedback && (
        <div
          role="status"
          className="rounded-[10px] bg-[#E6F2EE] border border-[#C6DFD7] px-4 py-3 text-[13px] text-[#1A5C4D]"
        >
          {feedback}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton variant="cards" />
      ) : (
        <ProfilLulusanOverview
          overview={overview}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          editable={isDraft}
          draftMatrix={draftMatrix}
          dirtyPlCount={dirtyPlIds.length}
          savingMatrix={savingMatrix}
          onToggleMatrixLink={handleToggleMatrixLink}
          onSaveMatrix={handleSaveMatrix}
          onResetMatrix={handleResetMatrix}
          listTopContent={createSection}
          renderCardActions={
            isDraft
              ? (pl) => (
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(pl.id);
                        setEditForm({
                          kode_pl: pl.kode_pl,
                          nama_pl: pl.nama_pl,
                          bidang_kerja: pl.bidang_kerja || '',
                          deskripsi: pl.deskripsi,
                        });
                      }}
                      className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium text-[#15333A] hover:bg-[#FAF8F3] cursor-pointer"
                    >
                      Ubah
                    </button>
                    <button
                      type="button"
                      disabled={busyId === pl.id}
                      onClick={() => handleDelete(pl)}
                      className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium text-[#B55824] hover:bg-[#F7EAE1] cursor-pointer disabled:opacity-60"
                    >
                      {busyId === pl.id ? 'Menghapus...' : 'Hapus'}
                    </button>
                  </div>
                )
              : undefined
          }
          renderEditingCard={(pl) => {
            if (!isDraft || editingId !== pl.id) return null;
            return (
              <section className="bg-white border-2 border-[#15333A]/30 rounded-[12px] p-6">
                <h3 className="text-[15px] font-semibold text-[#15333A] mb-3">
                  Ubah Profil Lulusan · {pl.kode_pl}
                </h3>
                <form onSubmit={handleUpdate} className="flex flex-col gap-3.5">
                  <div className="grid grid-cols-1 md:grid-cols-[150px_1fr_1fr] gap-3.5">
                    <input
                      type="text"
                      required
                      maxLength={10}
                      aria-label="Ubah kode PL"
                      value={editForm.kode_pl}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          kode_pl: e.target.value,
                        }))
                      }
                      className="h-[36px] px-3 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                    />
                    <input
                      type="text"
                      required
                      maxLength={150}
                      aria-label="Ubah nama PL"
                      value={editForm.nama_pl}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          nama_pl: e.target.value,
                        }))
                      }
                      className="h-[36px] px-3 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                    />
                    <input
                      type="text"
                      aria-label="Ubah bidang kerja"
                      value={editForm.bidang_kerja}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          bidang_kerja: e.target.value,
                        }))
                      }
                      placeholder="Bidang kerja (koma)..."
                      className="h-[36px] px-3 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                    />
                  </div>
                  <textarea
                    required
                    rows={2}
                    aria-label="Ubah deskripsi PL"
                    value={editForm.deskripsi}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        deskripsi: e.target.value,
                      }))
                    }
                    className="px-3 py-2 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                  />
                  <div className="flex items-center gap-2 justify-end">
                    <button
                      type="button"
                      onClick={() => setEditingId('')}
                      className="h-[34px] px-3.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium cursor-pointer"
                    >
                      Batal
                    </button>
                    <button
                      type="submit"
                      disabled={busyId === pl.id}
                      className="h-[34px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12px] font-semibold cursor-pointer disabled:opacity-60"
                    >
                      {busyId === pl.id ? 'Menyimpan...' : 'Simpan'}
                    </button>
                  </div>
                </form>
              </section>
            );
          }}
        />
      )}
    </div>
  );
}
