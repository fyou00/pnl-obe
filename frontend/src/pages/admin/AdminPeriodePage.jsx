import { useCallback, useEffect, useState } from 'react';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  closePeriode,
  createPeriode,
  deletePeriode,
  listPeriode,
  reopenPeriode,
  updatePeriode,
} from '../../lib/adminApi.js';

export default function AdminPeriodePage() {
  const { selectedPeriodId, setSelectedPeriodId, refreshPeriods } =
    useAdminWorkspace();

  const [periods, setPeriods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyId, setBusyId] = useState('');

  const [createForm, setCreateForm] = useState({
    tahun_mulai: new Date().getFullYear(),
    semester: 'Ganjil',
  });
  const [editingId, setEditingId] = useState('');
  const [editForm, setEditForm] = useState({
    tahun_mulai: 2026,
    semester: 'Ganjil',
  });
  const [closingId, setClosingId] = useState('');
  const [reopeningId, setReopeningId] = useState('');
  const [reopenReason, setReopenReason] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listPeriode({ limit: 100 });
      setPeriods(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat periode akademik.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyId('create');
    try {
      const created = await createPeriode(createForm);
      setFeedback(
        `Periode ${created.tahun_akademik} ${created.semester} berhasil dibuat.`,
      );
      await Promise.all([loadData(), refreshPeriods()]);
      setSelectedPeriodId(created.id);
    } catch (err) {
      setError(err.message || 'Gagal membuat periode akademik.');
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
      await updatePeriode(editingId, editForm);
      setEditingId('');
      setFeedback('Identitas periode akademik diperbarui.');
      await Promise.all([loadData(), refreshPeriods()]);
    } catch (err) {
      setError(err.message || 'Gagal memperbarui periode akademik.');
    } finally {
      setBusyId('');
    }
  };

  const handleDelete = async (item) => {
    setError('');
    setFeedback('');
    setBusyId(item.id);
    try {
      await deletePeriode(item.id);
      setFeedback(
        `Periode ${item.tahun_akademik} ${item.semester} berhasil dihapus.`,
      );
      await Promise.all([loadData(), refreshPeriods()]);
    } catch (err) {
      setError(err.message || 'Gagal menghapus periode akademik.');
    } finally {
      setBusyId('');
    }
  };

  const handleClosePeriod = async (item) => {
    setError('');
    setFeedback('');
    setBusyId(item.id);
    try {
      await closePeriode(item.id);
      setClosingId('');
      setFeedback(
        `Periode ${item.tahun_akademik} ${item.semester} berhasil ditutup dan dikunci.`,
      );
      await Promise.all([loadData(), refreshPeriods()]);
    } catch (err) {
      setError(err.message || 'Gagal menutup periode.');
    } finally {
      setBusyId('');
    }
  };

  const handleReopenPeriod = async (e, item) => {
    e.preventDefault();
    if (!reopenReason.trim()) {
      setError('Alasan pembukaan kembali periode wajib diisi.');
      return;
    }
    setError('');
    setFeedback('');
    setBusyId(item.id);
    try {
      await reopenPeriode(item.id, reopenReason.trim());
      setReopeningId('');
      setReopenReason('');
      setFeedback(
        `Periode ${item.tahun_akademik} ${item.semester} berhasil dibuka kembali (tercatat audit).`,
      );
      await Promise.all([loadData(), refreshPeriods()]);
    } catch (err) {
      setError(err.message || 'Gagal membuka kembali periode.');
    } finally {
      setBusyId('');
    }
  };

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
          Periode akademik
        </h1>
        <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
          Periode menggunakan tahun akademik (Ganjil/Genap, tanpa semester
          pendek). Penutupan mengunci paket, peserta, rancangan, dan nilai;
          pembukaan kembali memerlukan alasan audit.
        </p>
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

      <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
        <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
          Buka Periode Akademik Baru
        </h2>
        <form
          onSubmit={handleCreate}
          className="mt-4 grid grid-cols-[200px_220px_auto] gap-4 items-end"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
              Tahun mulai
            </label>
            <input
              type="number"
              required
              min={1900}
              max={9998}
              value={createForm.tahun_mulai}
              onChange={(e) =>
                setCreateForm((prev) => ({
                  ...prev,
                  tahun_mulai: e.target.value,
                }))
              }
              className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-[#525252] dark:text-[#A3A3A0]">
              Semester
            </label>
            <select
              value={createForm.semester}
              onChange={(e) =>
                setCreateForm((prev) => ({ ...prev, semester: e.target.value }))
              }
              className="h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
            >
              <option value="Ganjil">Ganjil</option>
              <option value="Genap">Genap</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={busyId === 'create'}
            className="h-[38px] px-4 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer w-fit"
          >
            {busyId === 'create' ? 'Menyimpan...' : '+ Buka Periode'}
          </button>
        </form>
      </section>

      <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6">
        <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4] mb-4">
          Daftar Periode Akademik ({periods.length})
        </h2>

        {loading ? (
          <p className="py-6 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Memuat periode...
          </p>
        ) : periods.length === 0 ? (
          <p className="py-6 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Belum ada periode akademik.
          </p>
        ) : (
          <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
            {periods.map((item) => {
              const isEditing = editingId === item.id;
              const isSelected = selectedPeriodId === item.id;
              const isClosing = closingId === item.id;
              const isReopening = reopeningId === item.id;

              return (
                <div key={item.id} className="py-4 flex flex-col gap-3">
                  {isEditing ? (
                    <form
                      onSubmit={handleUpdate}
                      className="grid grid-cols-[160px_180px_auto_auto] gap-3 items-center"
                    >
                      <input
                        type="number"
                        required
                        min={1900}
                        max={9998}
                        value={editForm.tahun_mulai}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            tahun_mulai: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                      />
                      <select
                        value={editForm.semester}
                        onChange={(e) =>
                          setEditForm((prev) => ({
                            ...prev,
                            semester: e.target.value,
                          }))
                        }
                        className="h-[34px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[13px]"
                      >
                        <option value="Ganjil">Ganjil</option>
                        <option value="Genap">Genap</option>
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
                        onClick={() => setEditingId('')}
                        className="h-[34px] px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                      >
                        Batal
                      </button>
                    </form>
                  ) : (
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <span className="text-[14px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                          {item.tahun_akademik} {item.semester}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full bg-[#F0F0EF] dark:bg-[#2A2A27] border border-[#E5E5E5] dark:border-[#343430] text-[11px] font-medium">
                          {item.status}
                        </span>
                        {isSelected && (
                          <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                            · Dipilih di topbar
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {!isSelected && (
                          <button
                            type="button"
                            onClick={() => setSelectedPeriodId(item.id)}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                          >
                            Pilih periode
                          </button>
                        )}
                        {item.status === 'Dibuka' ? (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingId(item.id);
                                setEditForm({
                                  tahun_mulai: item.tahun_mulai,
                                  semester: item.semester,
                                });
                              }}
                              className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                            >
                              Ubah
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setClosingId(item.id);
                                setReopeningId('');
                              }}
                              className="h-[30px] px-2.5 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                            >
                              Tutup periode
                            </button>
                            <button
                              type="button"
                              disabled={busyId === item.id}
                              onClick={() => handleDelete(item)}
                              className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] text-[#B55824] cursor-pointer"
                            >
                              Hapus
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              setReopeningId(item.id);
                              setClosingId('');
                              setReopenReason('');
                            }}
                            className="h-[30px] px-2.5 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] font-medium cursor-pointer"
                          >
                            Buka kembali
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {isClosing && (
                    <div className="rounded-[9px] bg-[#F5F5F4] dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] p-4 flex items-center justify-between gap-4">
                      <p className="text-[12.5px] text-[#525252] dark:text-[#D4D4D0]">
                        Tutup periode <strong>{item.tahun_akademik} {item.semester}</strong>? Paket, peserta, penugasan, rancangan, dan nilai akan terkunci.
                      </p>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          disabled={busyId === item.id}
                          onClick={() => handleClosePeriod(item)}
                          className="h-[32px] px-3 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                        >
                          {busyId === item.id ? 'Menutup...' : 'Ya, tutup periode'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setClosingId('')}
                          className="h-[32px] px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                        >
                          Batal
                        </button>
                      </div>
                    </div>
                  )}

                  {isReopening && (
                    <form
                      onSubmit={(e) => handleReopenPeriod(e, item)}
                      className="rounded-[9px] bg-[#F5F5F4] dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] p-4 flex flex-col gap-3"
                    >
                      <label
                        htmlFor={`reopen-reason-${item.id}`}
                        className="text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4]"
                      >
                        Alasan pembukaan kembali periode (wajib dicatat pada log audit)
                      </label>
                      <input
                        id={`reopen-reason-${item.id}`}
                        type="text"
                        required
                        maxLength={2000}
                        value={reopenReason}
                        onChange={(e) => setReopenReason(e.target.value)}
                        placeholder="Contoh: Koreksi nilai UAS kelas TI-3A sesuai berita acara prodi."
                        className="h-[36px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#343430] text-[13px]"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="submit"
                          disabled={busyId === item.id}
                          className="h-[32px] px-3 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer"
                        >
                          {busyId === item.id ? 'Membuka...' : 'Simpan & Buka Kembali'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setReopeningId('')}
                          className="h-[32px] px-3 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] text-[12px] cursor-pointer"
                        >
                          Batal
                        </button>
                      </div>
                    </form>
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
