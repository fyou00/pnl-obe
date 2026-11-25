import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { LockedPeriodBanner } from '../../components/states/SystemStates.jsx';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import {
  copyRancangan,
  createCpmk,
  createInstrumen,
  createSubCpmk,
  deleteCpmk,
  deleteInstrumen,
  deleteSubCpmk,
  getRancanganDetail,
  replaceCpmkCpl,
  updateCpmk,
  updateInstrumen,
  updateSubCpmk,
} from '../../lib/dosenApi.js';

const INSTRUMENT_KINDS = ['Tugas', 'Kuis', 'Praktikum', 'UTS', 'UAS'];

function formatWeight(value) {
  const num = Number(value ?? 0);
  return `${num.toFixed(2).replace('.', ',')}%`;
}

export default function DosenRancanganPage() {
  const { rancanganId } = useParams();
  const navigate = useNavigate();
  const {
    allDesigns,
    periodDesigns,
    selectedPeriod,
    classes,
    refreshDosenWorkspace,
  } = useDosenWorkspace();

  const activeId = rancanganId || periodDesigns[0]?.id || '';

  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busyKey, setBusyKey] = useState('');

  // Form tambah CPMK
  const [showAddCpmk, setShowAddCpmk] = useState(false);
  const [cpmkForm, setCpmkForm] = useState({
    kode_cpmk: '',
    deskripsi: '',
    cpl_ids: [],
  });
  const [editingCpmkId, setEditingCpmkId] = useState('');
  const [editCpmkForm, setEditCpmkForm] = useState({
    kode_cpmk: '',
    deskripsi: '',
  });

  // Form Sub-CPMK & Instrumen inline
  const [addingSubForCpmkId, setAddingSubForCpmkId] = useState('');
  const [subForm, setSubForm] = useState({ kode_sub: '', deskripsi: '' });
  const [editingSubId, setEditingSubId] = useState('');
  const [editSubForm, setEditSubForm] = useState({ kode_sub: '', deskripsi: '' });

  const [addingInstForSubId, setAddingInstForSubId] = useState('');
  const [instForm, setInstForm] = useState({
    nama_instrumen: '',
    jenis_instrumen: 'Tugas',
    bobot_persentase: '',
  });
  const [editingInstId, setEditingInstId] = useState('');
  const [editInstForm, setEditInstForm] = useState({
    nama_instrumen: '',
    jenis_instrumen: 'Tugas',
    bobot_persentase: '',
  });

  const [copySourceId, setCopySourceId] = useState('');
  const [chosenClassId, setChosenClassId] = useState('');

  const loadDetail = useCallback(async () => {
    if (!activeId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await getRancanganDetail(activeId);
      setDetail(data);
      setChosenClassId((prev) =>
        prev && data.kelas_pengguna.some((k) => k.kelas_mk_id === prev)
          ? prev
          : data.kelas_pengguna[0]?.kelas_mk_id || '',
      );
    } catch (err) {
      setError(err.message || 'Gagal memuat detail rancangan penilaian.');
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [activeId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const mkNameByDesignId = useMemo(() => {
    const map = {};
    for (const cls of classes) {
      map[cls.rancangan_id] = cls.nama_mk;
    }
    return map;
  }, [classes]);

  const copyCandidates = useMemo(() => {
    if (!detail) return [];
    return allDesigns.filter(
      (d) =>
        d.id !== detail.id &&
        d.kurikulum_mk_id === detail.kurikulum_mk_id &&
        Number(d.total_bobot) > 0,
    );
  }, [allDesigns, detail]);

  useEffect(() => {
    if (!copySourceId && copyCandidates[0]?.id) {
      setCopySourceId(copyCandidates[0].id);
    }
  }, [copyCandidates, copySourceId]);

  const cplById = useMemo(
    () =>
      Object.fromEntries((detail?.cpl_tersedia || []).map((c) => [c.id, c])),
    [detail?.cpl_tersedia],
  );

  const afterMutation = async (message) => {
    setFeedback(message);
    await Promise.all([loadDetail(), refreshDosenWorkspace()]);
  };

  const handleCopyDesign = async () => {
    if (!detail || !copySourceId) return;
    setError('');
    setFeedback('');
    setBusyKey('copy');
    try {
      await copyRancangan(detail.id, copySourceId);
      await afterMutation('Draft rancangan berhasil disalin dari periode sebelumnya.');
    } catch (err) {
      setError(err.message || 'Gagal menyalin rancangan.');
    } finally {
      setBusyKey('');
    }
  };

  const handleCreateCpmk = async (e) => {
    e.preventDefault();
    if (!detail) return;
    setError('');
    setFeedback('');
    setBusyKey('create-cpmk');
    try {
      await createCpmk(detail.id, cpmkForm);
      setCpmkForm({ kode_cpmk: '', deskripsi: '', cpl_ids: [] });
      setShowAddCpmk(false);
      await afterMutation('CPMK baru ditambahkan.');
    } catch (err) {
      setError(err.message || 'Gagal menambah CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleUpdateCpmk = async (e, cpmkId) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyKey(cpmkId);
    try {
      await updateCpmk(detail.id, cpmkId, editCpmkForm);
      setEditingCpmkId('');
      await afterMutation('CPMK diperbarui.');
    } catch (err) {
      setError(err.message || 'Gagal memperbarui CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteCpmk = async (cpmk) => {
    setError('');
    setFeedback('');
    setBusyKey(cpmk.id);
    try {
      await deleteCpmk(detail.id, cpmk.id);
      await afterMutation(`CPMK ${cpmk.kode_cpmk} dihapus.`);
    } catch (err) {
      setError(err.message || 'Gagal menghapus CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleToggleCpmkCpl = async (cpmk, cplId) => {
    if (detail.struktur_terkunci) return;
    setError('');
    setFeedback('');
    setBusyKey(`cpl-${cpmk.id}`);
    const exists = cpmk.cpl_ids.includes(cplId);
    const nextIds = exists
      ? cpmk.cpl_ids.filter((id) => id !== cplId)
      : [...cpmk.cpl_ids, cplId];
    try {
      await replaceCpmkCpl(detail.id, cpmk.id, nextIds);
      await afterMutation(`Pemetaan CPL untuk ${cpmk.kode_cpmk} diperbarui.`);
    } catch (err) {
      setError(err.message || 'Gagal memperbarui pemetaan CPL.');
    } finally {
      setBusyKey('');
    }
  };

  const handleCreateSub = async (e, cpmkId) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyKey(`sub-add-${cpmkId}`);
    try {
      await createSubCpmk(detail.id, cpmkId, subForm);
      setSubForm({ kode_sub: '', deskripsi: '' });
      setAddingSubForCpmkId('');
      await afterMutation('Sub-CPMK ditambahkan.');
    } catch (err) {
      setError(err.message || 'Gagal menambah Sub-CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleUpdateSub = async (e, cpmkId, subId) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    setBusyKey(subId);
    try {
      await updateSubCpmk(detail.id, cpmkId, subId, editSubForm);
      setEditingSubId('');
      await afterMutation('Sub-CPMK diperbarui.');
    } catch (err) {
      setError(err.message || 'Gagal memperbarui Sub-CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteSub = async (cpmkId, sub) => {
    setError('');
    setFeedback('');
    setBusyKey(sub.id);
    try {
      await deleteSubCpmk(detail.id, cpmkId, sub.id);
      await afterMutation(`Sub-CPMK ${sub.kode_sub} dihapus.`);
    } catch (err) {
      setError(err.message || 'Gagal menghapus Sub-CPMK.');
    } finally {
      setBusyKey('');
    }
  };

  const handleCreateInst = async (e, cpmkId, subId) => {
    e.preventDefault();
    const weight = Number(String(instForm.bobot_persentase).replace(',', '.'));
    if (Number.isNaN(weight) || weight <= 0 || weight > 100) {
      setError('Bobot instrumen harus lebih dari 0 dan maksimal 100%.');
      return;
    }
    setError('');
    setFeedback('');
    setBusyKey(`inst-add-${subId}`);
    try {
      await createInstrumen(detail.id, cpmkId, subId, instForm);
      setInstForm({
        nama_instrumen: '',
        jenis_instrumen: 'Tugas',
        bobot_persentase: '',
      });
      setAddingInstForSubId('');
      await afterMutation('Instrumen penilaian ditambahkan.');
    } catch (err) {
      setError(err.message || 'Gagal menambah instrumen.');
    } finally {
      setBusyKey('');
    }
  };

  const handleUpdateInst = async (e, cpmkId, subId, instId) => {
    e.preventDefault();
    const weight = Number(
      String(editInstForm.bobot_persentase).replace(',', '.'),
    );
    if (Number.isNaN(weight) || weight <= 0 || weight > 100) {
      setError('Bobot instrumen harus lebih dari 0 dan maksimal 100%.');
      return;
    }
    setError('');
    setFeedback('');
    setBusyKey(instId);
    try {
      await updateInstrumen(detail.id, cpmkId, subId, instId, editInstForm);
      setEditingInstId('');
      await afterMutation('Instrumen penilaian diperbarui.');
    } catch (err) {
      setError(err.message || 'Gagal memperbarui instrumen.');
    } finally {
      setBusyKey('');
    }
  };

  const handleDeleteInst = async (cpmkId, subId, inst) => {
    setError('');
    setFeedback('');
    setBusyKey(inst.id);
    try {
      await deleteInstrumen(detail.id, cpmkId, subId, inst.id);
      await afterMutation(`Instrumen "${inst.nama_instrumen}" dihapus.`);
    } catch (err) {
      setError(err.message || 'Gagal menghapus instrumen.');
    } finally {
      setBusyKey('');
    }
  };

  const totalWeightNum = Number(detail?.total_bobot ?? 0);
  const remainingWeight = Math.max(0, 100 - totalWeightNum);
  const activeMkName = detail ? mkNameByDesignId[detail.id] || 'Mata kuliah' : '';

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div className="flex flex-col gap-2">
          <Link
            to="/dosen"
            className="text-[13px] font-medium text-[#15333A] hover:underline w-fit"
          >
            ‹ Dashboard Dosen
          </Link>
          <h1 className="text-[32px] font-bold leading-[39px] text-[#15333A]">
            Rancangan Penilaian
          </h1>
          {detail && (
            <p className="text-[16px] text-[#334B51]">
              {activeMkName} / {detail.tahun_akademik} {detail.semester} /{' '}
              {detail.kelas_pengguna.map((k) => k.label).join(' dan ')}
            </p>
          )}
        </div>

        {periodDesigns.length > 1 && (
          <select
            aria-label="Pilih rancangan mata kuliah"
            value={activeId}
            onChange={(e) => navigate(`/dosen/rancangan/${e.target.value}`)}
            className="min-w-[230px] h-[38px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[12px] font-medium"
          >
            {periodDesigns.map((d) => (
              <option key={d.id} value={d.id}>
                {mkNameByDesignId[d.id] || 'Mata kuliah'} (
                {d.kelas_pengguna.map((k) => k.label).join(', ')})
              </option>
            ))}
          </select>
        )}
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

      {loading ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Memuat rancangan penilaian...
        </div>
      ) : !detail ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada rancangan penilaian pada periode terpilih.
        </div>
      ) : (
        <div className="grid grid-cols-[minmax(0,738fr)_minmax(0,374fr)] gap-6 items-start">
          {/* Kolom Kiri: Struktur Penilaian */}
          <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-5">
            <div className="flex items-start justify-between gap-4 border-b border-[#E4DFD4] pb-4">
              <div>
                <h2 className="text-[22px] font-semibold leading-[27px] text-[#15333A]">
                  Pemetaan dan instrumen
                </h2>
                <p className="text-[13px] text-[#566B70] mt-1">
                  Setiap instrumen menilai satu Sub-CPMK.
                </p>
              </div>

              {!detail.struktur_terkunci && (
                <button
                  type="button"
                  onClick={() => setShowAddCpmk((prev) => !prev)}
                  className="h-[38px] px-3.5 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] font-medium cursor-pointer shrink-0 hover:bg-[#FAF8F3]"
                >
                  + Tambah CPMK
                </button>
              )}
            </div>

            {/* Salin dari periode sebelumnya bila draft masih kosong */}
            {!detail.struktur_terkunci &&
              detail.cpmk.length === 0 &&
              copyCandidates.length > 0 && (
                <div className="rounded-[10px] bg-[#FAF8F3] border border-[#E4DFD4] p-4 flex items-center justify-between gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[13px] font-medium">
                      Salin dari rancangan periode sebelumnya
                    </span>
                    <span className="text-[12px] text-[#566B70]">
                      Hanya tersedia saat draft masih kosong pada MK kurikulum
                      yang sama.
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <select
                      aria-label="Pilih sumber rancangan"
                      value={copySourceId}
                      onChange={(e) => setCopySourceId(e.target.value)}
                      className="h-[34px] px-2.5 rounded-[7px] bg-white border border-[#E4DFD4] text-[12px]"
                    >
                      {copyCandidates.map((cand) => (
                        <option key={cand.id} value={cand.id}>
                          {cand.tahun_akademik} {cand.semester} (
                          {formatWeight(cand.total_bobot)})
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={busyKey === 'copy'}
                      onClick={handleCopyDesign}
                      className="h-[34px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
                    >
                      Salin draft
                    </button>
                  </div>
                </div>
              )}

            {/* Form Tambah CPMK */}
            {!detail.struktur_terkunci && showAddCpmk && (
              <form
                onSubmit={handleCreateCpmk}
                className="rounded-[10px] bg-[#FAF8F3] border border-[#E4DFD4] p-4 flex flex-col gap-3"
              >
                <div className="grid grid-cols-[160px_1fr] gap-3">
                  <input
                    type="text"
                    required
                    maxLength={20}
                    value={cpmkForm.kode_cpmk}
                    onChange={(e) =>
                      setCpmkForm((prev) => ({
                        ...prev,
                        kode_cpmk: e.target.value,
                      }))
                    }
                    placeholder="CPMK-01"
                    className="h-[36px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[13px]"
                  />
                  <input
                    type="text"
                    required
                    value={cpmkForm.deskripsi}
                    onChange={(e) =>
                      setCpmkForm((prev) => ({
                        ...prev,
                        deskripsi: e.target.value,
                      }))
                    }
                    placeholder="Deskripsi capaian mata kuliah"
                    className="h-[36px] px-3 rounded-[7px] bg-white border border-[#E4DFD4] text-[13px]"
                  />
                </div>

                {detail.cpl_tersedia.length > 0 && (
                  <div className="flex flex-wrap gap-3 pt-1">
                    {detail.cpl_tersedia.map((cpl) => (
                      <label
                        key={cpl.id}
                        className="inline-flex items-center gap-1.5 text-[12px] cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={cpmkForm.cpl_ids.includes(cpl.id)}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setCpmkForm((prev) => ({
                              ...prev,
                              cpl_ids: checked
                                ? [...prev.cpl_ids, cpl.id]
                                : prev.cpl_ids.filter((id) => id !== cpl.id),
                            }));
                          }}
                        />
                        <span>{cpl.kode_cpl}</span>
                      </label>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <button
                    type="submit"
                    disabled={busyKey === 'create-cpmk'}
                    className="h-[34px] px-3.5 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
                  >
                    Simpan CPMK
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddCpmk(false)}
                    className="h-[34px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                  >
                    Batal
                  </button>
                </div>
              </form>
            )}

            {/* Daftar CPMK */}
            {detail.cpmk.length === 0 ? (
              <p className="py-6 text-[13px] text-[#566B70]">
                Belum ada CPMK pada rancangan ini. Klik “+ Tambah CPMK” untuk
                memulai penyusunan.
              </p>
            ) : (
              <div className="divide-y divide-[#EFECE4]">
                {detail.cpmk.map((cpmk) => (
                  <div key={cpmk.id} className="py-5 first:pt-1 flex flex-col gap-4">
                    {/* Header CPMK */}
                    {editingCpmkId === cpmk.id ? (
                      <form
                        onSubmit={(e) => handleUpdateCpmk(e, cpmk.id)}
                        className="grid grid-cols-[140px_1fr_auto_auto] gap-2 items-center"
                      >
                        <input
                          type="text"
                          required
                          maxLength={20}
                          value={editCpmkForm.kode_cpmk}
                          onChange={(e) =>
                            setEditCpmkForm((prev) => ({
                              ...prev,
                              kode_cpmk: e.target.value,
                            }))
                          }
                          className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                        />
                        <input
                          type="text"
                          required
                          value={editCpmkForm.deskripsi}
                          onChange={(e) =>
                            setEditCpmkForm((prev) => ({
                              ...prev,
                              deskripsi: e.target.value,
                            }))
                          }
                          className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                        />
                        <button
                          type="submit"
                          disabled={busyKey === cpmk.id}
                          className="h-[34px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] font-medium cursor-pointer"
                        >
                          Simpan
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingCpmkId('')}
                          className="h-[34px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                        >
                          Batal
                        </button>
                      </form>
                    ) : (
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex flex-col gap-1">
                          <h3 className="text-[18px] font-semibold leading-[24px] text-[#15333A]">
                            {cpmk.kode_cpmk}{' '}
                            <span className="font-normal text-[16px]">
                              {cpmk.deskripsi}
                            </span>
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 mt-1">
                            {detail.struktur_terkunci ? (
                              cpmk.cpl_ids.length > 0 ? (
                                cpmk.cpl_ids.map((cid) => (
                                  <span
                                    key={cid}
                                    className="px-2.5 py-0.5 rounded bg-[#E6F0EE] text-[12px] font-medium"
                                  >
                                    {cplById[cid]?.kode_cpl || cid}
                                  </span>
                                ))
                              ) : (
                                <span className="text-[12px] text-[#B55824]">
                                  Belum dipetakan ke CPL
                                </span>
                              )
                            ) : (
                              <>
                                <span className="text-[11.5px] text-[#566B70]">
                                  Pemetaan CPL:
                                </span>
                                {detail.cpl_tersedia.map((cpl) => {
                                  const active = cpmk.cpl_ids.includes(cpl.id);
                                  return (
                                    <button
                                      key={cpl.id}
                                      type="button"
                                      disabled={busyKey === `cpl-${cpmk.id}`}
                                      onClick={() =>
                                        handleToggleCpmkCpl(cpmk, cpl.id)
                                      }
                                      className={[
                                        'h-[26px] px-2.5 rounded-[6px] text-[12px] font-medium border cursor-pointer transition-colors',
                                        active
                                          ? 'bg-[#15333A] border-[#15333A] text-white'
                                          : 'bg-[#FAF8F3] border-[#E4DFD4] text-[#334B51]',
                                      ].join(' ')}
                                    >
                                      {cpl.kode_cpl}
                                    </button>
                                  );
                                })}
                              </>
                            )}
                          </div>
                        </div>

                        {!detail.struktur_terkunci && (
                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              type="button"
                              onClick={() => {
                                setEditingCpmkId(cpmk.id);
                                setEditCpmkForm({
                                  kode_cpmk: cpmk.kode_cpmk,
                                  deskripsi: cpmk.deskripsi,
                                });
                              }}
                              className="h-[28px] px-2.5 rounded-[6px] border border-[#E4DFD4] text-[11.5px] cursor-pointer"
                            >
                              Ubah
                            </button>
                            <button
                              type="button"
                              disabled={busyKey === cpmk.id}
                              onClick={() => handleDeleteCpmk(cpmk)}
                              className="h-[28px] px-2.5 rounded-[6px] border border-[#E4DFD4] text-[11.5px] text-[#B55824] cursor-pointer"
                            >
                              Hapus
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Daftar Sub-CPMK */}
                    <div className="pl-4 flex flex-col gap-3">
                      {cpmk.sub_cpmk.map((sub) => (
                        <div key={sub.id} className="flex flex-col gap-2">
                          {editingSubId === sub.id ? (
                            <form
                              onSubmit={(e) =>
                                handleUpdateSub(e, cpmk.id, sub.id)
                              }
                              className="grid grid-cols-[140px_1fr_auto_auto] gap-2 items-center"
                            >
                              <input
                                type="text"
                                required
                                maxLength={20}
                                value={editSubForm.kode_sub}
                                onChange={(e) =>
                                  setEditSubForm((prev) => ({
                                    ...prev,
                                    kode_sub: e.target.value,
                                  }))
                                }
                                className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                              />
                              <input
                                type="text"
                                required
                                value={editSubForm.deskripsi}
                                onChange={(e) =>
                                  setEditSubForm((prev) => ({
                                    ...prev,
                                    deskripsi: e.target.value,
                                  }))
                                }
                                className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                              />
                              <button
                                type="submit"
                                disabled={busyKey === sub.id}
                                className="h-[32px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] cursor-pointer"
                              >
                                Simpan
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingSubId('')}
                                className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                              >
                                Batal
                              </button>
                            </form>
                          ) : (
                            <div className="flex items-center justify-between gap-4">
                              <p className="text-[15px] text-[#15333A]">
                                <span className="font-medium">
                                  {sub.kode_sub}
                                </span>{' '}
                                {sub.deskripsi}
                              </p>
                              {!detail.struktur_terkunci && (
                                <div className="flex items-center gap-2 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setAddingInstForSubId(sub.id);
                                      setInstForm({
                                        nama_instrumen: '',
                                        jenis_instrumen: 'Tugas',
                                        bobot_persentase: '',
                                      });
                                    }}
                                    className="h-[26px] px-2.5 rounded-[6px] border border-[#E4DFD4] text-[11.5px] cursor-pointer"
                                  >
                                    + Instrumen
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setEditingSubId(sub.id);
                                      setEditSubForm({
                                        kode_sub: sub.kode_sub,
                                        deskripsi: sub.deskripsi,
                                      });
                                    }}
                                    className="h-[26px] px-2 rounded-[6px] border border-[#E4DFD4] text-[11.5px] cursor-pointer"
                                  >
                                    Ubah
                                  </button>
                                  <button
                                    type="button"
                                    disabled={busyKey === sub.id}
                                    onClick={() => handleDeleteSub(cpmk.id, sub)}
                                    className="h-[26px] px-2 rounded-[6px] border border-[#E4DFD4] text-[11.5px] text-[#B55824] cursor-pointer"
                                  >
                                    Hapus
                                  </button>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Daftar Instrumen */}
                          <div className="pl-4 flex flex-col gap-1.5">
                            {sub.instrumen.map((inst) =>
                              editingInstId === inst.id ? (
                                <form
                                  key={inst.id}
                                  onSubmit={(e) =>
                                    handleUpdateInst(
                                      e,
                                      cpmk.id,
                                      sub.id,
                                      inst.id,
                                    )
                                  }
                                  className="grid grid-cols-[1fr_120px_90px_auto_auto] gap-2 items-center py-1"
                                >
                                  <input
                                    type="text"
                                    required
                                    maxLength={100}
                                    value={editInstForm.nama_instrumen}
                                    onChange={(e) =>
                                      setEditInstForm((prev) => ({
                                        ...prev,
                                        nama_instrumen: e.target.value,
                                      }))
                                    }
                                    className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                                  />
                                  <select
                                    value={editInstForm.jenis_instrumen}
                                    onChange={(e) =>
                                      setEditInstForm((prev) => ({
                                        ...prev,
                                        jenis_instrumen: e.target.value,
                                      }))
                                    }
                                    className="h-[32px] px-2 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12px]"
                                  >
                                    {INSTRUMENT_KINDS.map((kind) => (
                                      <option key={kind} value={kind}>
                                        {kind}
                                      </option>
                                    ))}
                                  </select>
                                  <input
                                    type="text"
                                    required
                                    value={editInstForm.bobot_persentase}
                                    onChange={(e) =>
                                      setEditInstForm((prev) => ({
                                        ...prev,
                                        bobot_persentase: e.target.value,
                                      }))
                                    }
                                    className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[13px]"
                                  />
                                  <button
                                    type="submit"
                                    disabled={busyKey === inst.id}
                                    className="h-[32px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] cursor-pointer"
                                  >
                                    Simpan
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setEditingInstId('')}
                                    className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                                  >
                                    Batal
                                  </button>
                                </form>
                              ) : (
                                <div
                                  key={inst.id}
                                  className="flex items-center justify-between gap-4 py-1 text-[14px]"
                                >
                                  <div className="flex items-center gap-2.5">
                                    <span>{inst.nama_instrumen}</span>
                                    <span className="px-2 py-0.5 rounded bg-[#E6F0EE] text-[11px] text-[#334B51]">
                                      {inst.jenis_instrumen}
                                    </span>
                                  </div>

                                  <div className="flex items-center gap-3 shrink-0">
                                    <span className="font-medium tabular-nums">
                                      {formatWeight(inst.bobot_persentase)}
                                    </span>
                                    {!detail.struktur_terkunci && (
                                      <div className="flex items-center gap-1.5">
                                        <button
                                          type="button"
                                          onClick={() => {
                                            setEditingInstId(inst.id);
                                            setEditInstForm({
                                              nama_instrumen:
                                                inst.nama_instrumen,
                                              jenis_instrumen:
                                                inst.jenis_instrumen,
                                              bobot_persentase: String(
                                                Number(inst.bobot_persentase),
                                              ),
                                            });
                                          }}
                                          className="text-[11.5px] text-[#566B70] hover:text-[#15333A] cursor-pointer"
                                        >
                                          Ubah
                                        </button>
                                        <button
                                          type="button"
                                          disabled={busyKey === inst.id}
                                          onClick={() =>
                                            handleDeleteInst(
                                              cpmk.id,
                                              sub.id,
                                              inst,
                                            )
                                          }
                                          className="text-[11.5px] text-[#B55824] cursor-pointer"
                                        >
                                          Hapus
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ),
                            )}

                            {/* Form tambah instrumen */}
                            {!detail.struktur_terkunci &&
                              addingInstForSubId === sub.id && (
                                <form
                                  onSubmit={(e) =>
                                    handleCreateInst(e, cpmk.id, sub.id)
                                  }
                                  className="grid grid-cols-[1fr_120px_90px_auto_auto] gap-2 items-center pt-1"
                                >
                                  <input
                                    type="text"
                                    required
                                    maxLength={100}
                                    value={instForm.nama_instrumen}
                                    onChange={(e) =>
                                      setInstForm((prev) => ({
                                        ...prev,
                                        nama_instrumen: e.target.value,
                                      }))
                                    }
                                    placeholder="Nama instrumen"
                                    className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12.5px]"
                                  />
                                  <select
                                    value={instForm.jenis_instrumen}
                                    onChange={(e) =>
                                      setInstForm((prev) => ({
                                        ...prev,
                                        jenis_instrumen: e.target.value,
                                      }))
                                    }
                                    className="h-[32px] px-2 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12px]"
                                  >
                                    {INSTRUMENT_KINDS.map((kind) => (
                                      <option key={kind} value={kind}>
                                        {kind}
                                      </option>
                                    ))}
                                  </select>
                                  <input
                                    type="text"
                                    required
                                    value={instForm.bobot_persentase}
                                    onChange={(e) =>
                                      setInstForm((prev) => ({
                                        ...prev,
                                        bobot_persentase: e.target.value,
                                      }))
                                    }
                                    placeholder="Bobot %"
                                    className="h-[32px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12.5px]"
                                  />
                                  <button
                                    type="submit"
                                    disabled={busyKey === `inst-add-${sub.id}`}
                                    className="h-[32px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] cursor-pointer"
                                  >
                                    Tambah
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setAddingInstForSubId('')}
                                    className="h-[32px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                                  >
                                    Batal
                                  </button>
                                </form>
                              )}
                          </div>
                        </div>
                      ))}

                      {!detail.struktur_terkunci && (
                        <div className="pt-1">
                          {addingSubForCpmkId === cpmk.id ? (
                            <form
                              onSubmit={(e) => handleCreateSub(e, cpmk.id)}
                              className="grid grid-cols-[150px_1fr_auto_auto] gap-2 items-center"
                            >
                              <input
                                type="text"
                                required
                                maxLength={20}
                                value={subForm.kode_sub}
                                onChange={(e) =>
                                  setSubForm((prev) => ({
                                    ...prev,
                                    kode_sub: e.target.value,
                                  }))
                                }
                                placeholder="Sub-CPMK 1.1"
                                className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12.5px]"
                              />
                              <input
                                type="text"
                                required
                                value={subForm.deskripsi}
                                onChange={(e) =>
                                  setSubForm((prev) => ({
                                    ...prev,
                                    deskripsi: e.target.value,
                                  }))
                                }
                                placeholder="Deskripsi Sub-CPMK"
                                className="h-[34px] px-2.5 rounded-[7px] border border-[#E4DFD4] bg-[#FAF8F3] text-[12.5px]"
                              />
                              <button
                                type="submit"
                                disabled={busyKey === `sub-add-${cpmk.id}`}
                                className="h-[34px] px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12px] cursor-pointer"
                              >
                                Simpan
                              </button>
                              <button
                                type="button"
                                onClick={() => setAddingSubForCpmkId('')}
                                className="h-[34px] px-3 rounded-[7px] border border-[#E4DFD4] text-[12px] cursor-pointer"
                              >
                                Batal
                              </button>
                            </form>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setAddingSubForCpmkId(cpmk.id);
                                setSubForm({ kode_sub: '', deskripsi: '' });
                              }}
                              className="h-[34px] px-3.5 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px] font-medium cursor-pointer hover:bg-[#FAF8F3]"
                            >
                              + Sub-CPMK
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Kolom Kanan: Kesiapan & Kelas Pengguna */}
          <div className="flex flex-col gap-6">
            <section className="min-h-[346px] bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-2">
                <h2 className="text-[22px] font-semibold leading-[27px] text-[#15333A]">
                  Kesiapan rancangan
                </h2>
                <p className="text-[18px] font-semibold mt-2">
                  {detail.struktur_terkunci
                    ? 'Struktur terkunci'
                    : detail.siap_dinilai
                      ? 'Siap dinilai'
                      : 'Belum siap dinilai'}
                </p>
                {detail.struktur_terkunci ? (
                  <p className="text-[13px] text-[#566B70]">
                    {detail.alasan_terkunci || 'Nilai pertama sudah diinput.'}
                  </p>
                ) : detail.alasan_belum_siap.length > 0 ? (
                  <ul className="text-[13px] text-[#B55824] space-y-1">
                    {detail.alasan_belum_siap.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[13px] text-[#1A5C4D]">
                    Seluruh CPMK terpetakan dan bobot mencapai 100%.
                  </p>
                )}
              </div>

              <div className="border-t border-[#E4DFD4] pt-5 flex flex-col gap-2">
                <span className="text-[14px] text-[#566B70]">
                  Total bobot instrumen
                </span>
                <span className="text-[31px] font-bold leading-[38px] tabular-nums">
                  {Number(detail.total_bobot).toFixed(0)} / 100%
                </span>
                <span className="text-[13px] text-[#566B70]">
                  {totalWeightNum === 100
                    ? `Pemetaan lengkap · ${detail.cpmk.filter((c) => c.cpl_ids.length > 0).length} dari ${detail.cpmk.length} CPMK`
                    : remainingWeight > 0
                      ? `Tambahkan ${remainingWeight.toFixed(2).replace('.', ',')}% bobot pada rancangan.`
                      : `Kelebihan ${(totalWeightNum - 100).toFixed(2).replace('.', ',')}% bobot pada rancangan.`}
                </span>
              </div>
            </section>

            <section className="min-h-[324px] bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-3">
                <h2 className="text-[21px] font-semibold leading-[27px] text-[#15333A]">
                  Kelas pengguna rancangan
                </h2>
                <p className="text-[18px] text-[#15333A]">
                  {detail.kelas_pengguna.map((k) => k.label).join(' dan ')}
                </p>
                <p className="text-[13px] leading-[19px] text-[#566B70]">
                  {detail.siap_dinilai
                    ? 'Instrumen dan bobot dipakai bersama. Pilih kelas untuk pengisian nilai.'
                    : 'Penilaian tersedia setelah setiap CPMK terpetakan dan bobot mencapai 100%.'}
                </p>
              </div>

              {detail.siap_dinilai && detail.kelas_pengguna.length > 0 && (
                <div className="flex flex-col gap-3">
                  <select
                    aria-label="Pilih kelas untuk input nilai"
                    value={chosenClassId}
                    onChange={(e) => setChosenClassId(e.target.value)}
                    className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px] font-medium"
                  >
                    {detail.kelas_pengguna.map((k) => (
                      <option key={k.kelas_mk_id} value={k.kelas_mk_id}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                  <Link
                    to={`/dosen/nilai/${chosenClassId}`}
                    className="h-[38px] px-4 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[13px] font-medium inline-flex items-center justify-center"
                  >
                    Buka input nilai →
                  </Link>
                </div>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
