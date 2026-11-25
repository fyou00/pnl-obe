import { useCallback, useEffect, useState } from 'react';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  activateKurikulum,
  archiveKurikulum,
  cloneKurikulum,
  createKurikulum,
  deleteKurikulum,
  listKurikulum,
  updateKurikulum,
} from '../../lib/adminApi.js';

export default function AdminKurikulumPage() {
  const {
    selectedCurriculumId,
    setSelectedCurriculumId,
    refreshCurricula,
  } = useAdminWorkspace();

  const [items, setItems] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const [createForm, setCreateForm] = useState({
    kode_kurikulum: '',
    nama: '',
  });
  const [editingId, setEditingId] = useState('');
  const [editForm, setEditForm] = useState({ kode_kurikulum: '', nama: '' });
  const [cloningId, setCloningId] = useState('');
  const [cloneForm, setCloneForm] = useState({ kode_kurikulum: '', nama: '' });
  const [busyId, setBusyId] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listKurikulum({
        limit: 100,
        status: statusFilter || undefined,
        q: searchQuery.trim() || undefined,
      });
      setItems(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat daftar kurikulum.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId('create');
    try {
      const created = await createKurikulum(createForm);
      setCreateForm({ kode_kurikulum: '', nama: '' });
      setFeedback(`Kurikulum Draft "${created.nama}" berhasil dibuat.`);
      await Promise.all([loadData(), refreshCurricula()]);
      setSelectedCurriculumId(created.id);
    } catch (err) {
      setError(err.message || 'Gagal membuat kurikulum.');
    } finally {
      setBusyId('');
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId(editingId);
    try {
      await updateKurikulum(editingId, editForm);
      setEditingId('');
      setFeedback('Perubahan kurikulum Draft berhasil disimpan.');
      await Promise.all([loadData(), refreshCurricula()]);
    } catch (err) {
      setError(err.message || 'Gagal memperbarui kurikulum.');
    } finally {
      setBusyId('');
    }
  };

  const handleTransition = async (item, action) => {
    setError('');
    setFeedback('');
    setBusyId(item.id);
    try {
      if (action === 'activate') {
        await activateKurikulum(item.id);
        setFeedback(`Kurikulum "${item.nama}" diaktifkan.`);
      } else if (action === 'archive') {
        await archiveKurikulum(item.id);
        setFeedback(`Kurikulum "${item.nama}" diarsipkan.`);
      } else if (action === 'delete') {
        await deleteKurikulum(item.id);
        setFeedback(`Kurikulum Draft "${item.nama}" dihapus.`);
      }
      await Promise.all([loadData(), refreshCurricula()]);
    } catch (err) {
      setError(err.message || 'Tindakan gagal dijalankan.');
    } finally {
      setBusyId('');
    }
  };

  const handleClone = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId(cloningId);
    try {
      const cloned = await cloneKurikulum(cloningId, cloneForm);
      setCloningId('');
      setCloneForm({ kode_kurikulum: '', nama: '' });
      setFeedback(
        `Versi Draft baru "${cloned.nama}" berhasil disalin beserta CPL, MK, dan matriksnya.`,
      );
      await Promise.all([loadData(), refreshCurricula()]);
      setSelectedCurriculumId(cloned.id);
    } catch (err) {
      setError(err.message || 'Gagal menyalin kurikulum.');
    } finally {
      setBusyId('');
    }
  };

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
            Versi Kurikulum
          </h1>
          <p className="text-[14px] text-[#566B70] mt-2">
            Kurikulum Aktif dan Arsip bersifat read-only. Revisi isi dilakukan
            melalui salinan versi Draft baru.
          </p>
        </div>
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

      {/* Form tambah Draft */}
      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6">
        <h2 className="text-[17px] font-semibold text-[#15333A]">
          Buat Versi Kurikulum Draft
        </h2>
        <form
          onSubmit={handleCreate}
          className="mt-4 grid grid-cols-[240px_1fr_auto] gap-4 items-end"
        >
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="kur-kode"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Kode kurikulum
            </label>
            <input
              id="kur-kode"
              type="text"
              required
              maxLength={30}
              value={createForm.kode_kurikulum}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  kode_kurikulum: e.target.value,
                }))
              }
              placeholder="TI-2026"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="kur-nama"
              className="text-[12px] font-medium text-[#334B51]"
            >
              Nama versi kurikulum
            </label>
            <input
              id="kur-nama"
              type="text"
              required
              maxLength={100}
              value={createForm.nama}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, nama: e.target.value }))
              }
              placeholder="Kurikulum TI 2026"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
          </div>

          <button
            type="submit"
            disabled={busyId === 'create'}
            className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer disabled:opacity-60"
          >
            {busyId === 'create' ? 'Menyimpan...' : '+ Buat Draft'}
          </button>
        </form>
      </section>

      {/* Form salin kurikulum */}
      {cloningId && (
        <section className="bg-white border border-[#15333A] rounded-[12px] p-6">
          <h2 className="text-[16px] font-semibold text-[#15333A]">
            Salin ke Versi Draft Baru
          </h2>
          <form
            onSubmit={handleClone}
            className="mt-4 grid grid-cols-[240px_1fr_auto_auto] gap-4 items-end"
          >
            <input
              type="text"
              required
              maxLength={30}
              value={cloneForm.kode_kurikulum}
              onChange={(e) =>
                setCloneForm((prev) => ({
                  ...prev,
                  kode_kurikulum: e.target.value,
                }))
              }
              placeholder="Kode baru (mis. TI-2027)"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
            <input
              type="text"
              required
              maxLength={100}
              value={cloneForm.nama}
              onChange={(e) =>
                setCloneForm((prev) => ({ ...prev, nama: e.target.value }))
              }
              placeholder="Nama versi kurikulum baru"
              className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
            />
            <button
              type="submit"
              disabled={busyId === cloningId}
              className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
            >
              Salin
            </button>
            <button
              type="button"
              onClick={() => setCloningId('')}
              className="h-[38px] px-4 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
            >
              Batal
            </button>
          </form>
        </section>
      )}

      {/* Daftar Kurikulum */}
      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-[17px] font-semibold text-[#15333A]">
            Daftar Versi Kurikulum
          </h2>

          <div className="flex items-center gap-3">
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kode atau nama..."
              className="h-[36px] w-[220px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
            />
            <select
              aria-label="Filter status kurikulum"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-[36px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px]"
            >
              <option value="">Semua status</option>
              <option value="Draft">Draft</option>
              <option value="Aktif">Aktif</option>
              <option value="Arsip">Arsip</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-8 text-[13px] text-[#566B70]">
            Memuat daftar kurikulum...
          </div>
        ) : items.length === 0 ? (
          <div className="py-8 text-[13px] text-[#566B70]">
            Belum ada versi kurikulum.
          </div>
        ) : (
          <div className="divide-y divide-[#EFECE4]">
            {items.map((item) => {
              const isEditing = editingId === item.id;
              const isSelected = selectedCurriculumId === item.id;
              return (
                <div
                  key={item.id}
                  className="py-4 flex items-center justify-between gap-4"
                >
                  {isEditing ? (
                    <form
                      onSubmit={handleSaveEdit}
                      className="flex-1 grid grid-cols-[200px_1fr_auto_auto] gap-3 items-center"
                    >
                      <input
                        type="text"
                        required
                        maxLength={30}
                        value={editForm.kode_kurikulum}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            kode_kurikulum: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                      />
                      <input
                        type="text"
                        required
                        maxLength={100}
                        value={editForm.nama}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            nama: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                      />
                      <button
                        type="submit"
                        disabled={busyId === item.id}
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
                    <>
                      <div className="flex flex-col gap-1 min-w-0">
                        <div className="flex items-center gap-2.5">
                          <span className="text-[14px] font-semibold text-[#15333A]">
                            {item.nama}
                          </span>
                          <span className="px-2.5 py-0.5 rounded-full bg-[#E6F0EE] border border-[#E4DFD4] text-[11px] font-medium">
                            {item.status}
                          </span>
                          {isSelected && (
                            <span className="text-[11px] text-[#566B70]">
                              · Konteks aktif
                            </span>
                          )}
                        </div>
                        <span className="text-[12px] text-[#566B70]">
                          Kode: {item.kode_kurikulum}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {!isSelected && (
                          <button
                            type="button"
                            onClick={() => setSelectedCurriculumId(item.id)}
                            className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer hover:bg-[#FAF8F3]"
                          >
                            Pilih konteks
                          </button>
                        )}
                        {item.status === 'Draft' && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingId(item.id);
                                setEditForm({
                                  kode_kurikulum: item.kode_kurikulum,
                                  nama: item.nama,
                                });
                              }}
                              className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                            >
                              Ubah
                            </button>
                            <button
                              type="button"
                              disabled={busyId === item.id}
                              onClick={() => handleTransition(item, 'activate')}
                              className="h-[32px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
                            >
                              Aktifkan
                            </button>
                            <button
                              type="button"
                              disabled={busyId === item.id}
                              onClick={() => handleTransition(item, 'delete')}
                              className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] text-[#B55824] cursor-pointer"
                            >
                              Hapus
                            </button>
                          </>
                        )}
                        {item.status === 'Aktif' && (
                          <button
                            type="button"
                            disabled={busyId === item.id}
                            onClick={() => handleTransition(item, 'archive')}
                            className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                          >
                            Arsipkan
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            setCloningId(item.id);
                            setCloneForm({
                              kode_kurikulum: `${item.kode_kurikulum}-REV`,
                              nama: `${item.nama} (Revisi)`,
                            });
                          }}
                          className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                        >
                          Salin versi baru
                        </button>
                      </div>
                    </>
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
