import { useCallback, useEffect, useState } from 'react';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  createCpl,
  deleteCpl,
  listCpl,
  updateCpl,
} from '../../lib/adminApi.js';

const KATEGORI_OPTIONS = [
  { value: 'S', label: 'S · Sikap' },
  { value: 'KU', label: 'KU · Keterampilan Umum' },
  { value: 'P', label: 'P · Pengetahuan' },
  { value: 'KK', label: 'KK · Keterampilan Khusus' },
];

export default function AdminCplPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedCurriculum,
  } = useAdminWorkspace();

  const [cpls, setCpls] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyId, setBusyId] = useState('');

  const [createForm, setCreateForm] = useState({
    kode_cpl: '',
    kategori: 'KK',
    deskripsi: '',
    nasional: false,
  });
  const [editingId, setEditingId] = useState('');
  const [editForm, setEditForm] = useState({
    kode_cpl: '',
    kategori: 'KK',
    deskripsi: '',
    nasional: false,
  });

  const isDraft = selectedCurriculum?.status === 'Draft';

  const loadCpls = useCallback(async () => {
    if (!selectedCurriculumId) {
      setCpls([]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await listCpl(selectedCurriculumId, {
        limit: 100,
        q: searchQuery.trim() || undefined,
      });
      setCpls(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat Master CPL.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCurriculumId]);

  useEffect(() => {
    loadCpls();
  }, [loadCpls]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!selectedCurriculumId) return;
    setError('');
    setFeedback('');
    setBusyId('create');
    try {
      await createCpl(selectedCurriculumId, createForm);
      setCreateForm({
        kode_cpl: '',
        kategori: 'KK',
        deskripsi: '',
        nasional: false,
      });
      setFeedback('CPL baru berhasil ditambahkan ke kurikulum Draft.');
      await loadCpls();
    } catch (err) {
      setError(err.message || 'Gagal menambah CPL.');
    } finally {
      setBusyId('');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId(editingId);
    try {
      await updateCpl(selectedCurriculumId, editingId, editForm);
      setEditingId('');
      setFeedback('CPL berhasil diperbarui.');
      await loadCpls();
    } catch (err) {
      setError(err.message || 'Gagal memperbarui CPL.');
    } finally {
      setBusyId('');
    }
  };

  const handleDelete = async (cpl) => {
    setError('');
    setFeedback('');
    setBusyId(cpl.id);
    try {
      await deleteCpl(selectedCurriculumId, cpl.id);
      setFeedback(`CPL ${cpl.kode_cpl} dihapus.`);
      await loadCpls();
    } catch (err) {
      setError(err.message || 'Gagal menghapus CPL.');
    } finally {
      setBusyId('');
    }
  };

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Master CPL
          </h1>
          <p className="text-[14px] text-[#566B70] mt-2">
            Kelola Capaian Pembelajaran Lulusan per versi kurikulum. Perubahan
            hanya diizinkan pada kurikulum berstatus Draft.
          </p>
        </div>

        <select
          aria-label="Pilih versi kurikulum"
          value={selectedCurriculumId}
          onChange={(e) => setSelectedCurriculumId(e.target.value)}
          disabled={curricula.length === 0}
          className="min-w-[218px] h-[38px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[12px] font-medium"
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
          menjadi versi Draft di menu Versi kurikulum bila perlu mengubah CPL.
        </div>
      )}

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

      {isDraft && (
        <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6">
          <h2 className="text-[17px] font-semibold text-[#15333A]">
            Tambah Master CPL
          </h2>
          <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-4">
            <div className="grid grid-cols-[180px_240px_1fr] gap-4 items-end">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Kode CPL
                </label>
                <input
                  type="text"
                  required
                  maxLength={10}
                  value={createForm.kode_cpl}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      kode_cpl: e.target.value,
                    }))
                  }
                  placeholder="CPL-01"
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Kategori
                </label>
                <select
                  value={createForm.kategori}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      kategori: e.target.value,
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                >
                  {KATEGORI_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <label className="h-[38px] inline-flex items-center gap-2 text-[13px] text-[#15333A] cursor-pointer">
                <input
                  type="checkbox"
                  checked={createForm.nasional}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      nasional: e.target.checked,
                    }))
                  }
                />
                <span>CPL Nasional (lintas prodi)</span>
              </label>
            </div>

            <div className="grid grid-cols-[1fr_auto] gap-4 items-end">
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-[#334B51]">
                  Deskripsi CPL
                </label>
                <input
                  type="text"
                  required
                  value={createForm.deskripsi}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      deskripsi: e.target.value,
                    }))
                  }
                  placeholder="Mampu merancang dan mengimplementasikan sistem..."
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <button
                type="submit"
                disabled={busyId === 'create'}
                className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
              >
                {busyId === 'create' ? 'Menyimpan...' : '+ Tambah CPL'}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-[17px] font-semibold text-[#15333A]">
            Daftar CPL ({cpls.length})
          </h2>

          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cari kode atau deskripsi..."
            className="h-[36px] w-[240px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
          />
        </div>

        {loading ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Memuat daftar CPL...
          </p>
        ) : cpls.length === 0 ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Belum ada CPL pada kurikulum ini.
          </p>
        ) : (
          <div className="divide-y divide-[#EFECE4]">
            {cpls.map((cpl) => {
              const isEditing = editingId === cpl.id;
              return (
                <div key={cpl.id} className="py-4">
                  {isEditing ? (
                    <form
                      onSubmit={handleUpdate}
                      className="grid grid-cols-[120px_120px_1fr_auto_auto_auto] gap-3 items-center"
                    >
                      <input
                        type="text"
                        required
                        maxLength={10}
                        value={editForm.kode_cpl}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            kode_cpl: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                      />
                      <select
                        value={editForm.kategori}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            kategori: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                      >
                        {KATEGORI_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.value}
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        required
                        value={editForm.deskripsi}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            deskripsi: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                      />
                      <label className="text-[12px] inline-flex items-center gap-1.5">
                        <input
                          type="checkbox"
                          checked={editForm.nasional}
                          onChange={(e) =>
                            setEditForm((prev) => ({
                              ...prev,
                              nasional: e.target.checked,
                            }))
                          }
                        />
                        <span>Nasional</span>
                      </label>
                      <button
                        type="submit"
                        disabled={busyId === cpl.id}
                        className="h-[34px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
                      >
                        Simpan
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId('')}
                        className="h-[34px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                      >
                        Batal
                      </button>
                    </form>
                  ) : (
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-4 min-w-0">
                        <span className="w-[84px] shrink-0 text-[13px] font-semibold text-[#15333A]">
                          {cpl.kode_cpl}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-[#E6F0EE] text-[11px] font-medium shrink-0">
                          {cpl.kategori}
                        </span>
                        <div className="flex flex-col gap-1 min-w-0">
                          <p className="text-[13px] leading-[19px] text-[#15333A]">
                            {cpl.deskripsi}
                          </p>
                          <span className="text-[11px] text-[#566B70]">
                            {cpl.prodi_id === null ? 'Nasional' : 'Program Studi'}
                          </span>
                        </div>
                      </div>

                      {isDraft && (
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => {
                              setEditingId(cpl.id);
                              setEditForm({
                                kode_cpl: cpl.kode_cpl,
                                kategori: cpl.kategori,
                                deskripsi: cpl.deskripsi,
                                nasional: cpl.prodi_id === null,
                              });
                            }}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                          >
                            Ubah
                          </button>
                          <button
                            type="button"
                            disabled={busyId === cpl.id}
                            onClick={() => handleDelete(cpl)}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] text-[#B55824] cursor-pointer"
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
    </div>
  );
}
