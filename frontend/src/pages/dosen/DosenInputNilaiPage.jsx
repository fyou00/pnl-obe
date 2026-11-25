import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import {
  getKelasMkCapaian,
  getKelasMkNilai,
  getKelasMkPeserta,
} from '../../lib/adminApi.js';
import { getKelasRancangan, saveKelasMkNilai } from '../../lib/dosenApi.js';

function formatSavedScore(val) {
  if (val === null || val === undefined || val === '') return '';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return Number.isInteger(num) ? String(num) : num.toFixed(2).replace(/\.?0+$/, '');
}

function validateScoreInput(rawValue, hasSavedServerValue) {
  const trimmed = String(rawValue ?? '').trim();
  if (trimmed === '') {
    return hasSavedServerValue ? 'Masukkan nilai 0–100' : '';
  }
  const normalized = trimmed.replace(',', '.');
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return 'Masukkan nilai 0–100';
  }
  const num = Number(normalized);
  if (Number.isNaN(num) || num < 0 || num > 100) {
    return 'Masukkan nilai 0–100';
  }
  return '';
}

export default function DosenInputNilaiPage() {
  const { kelasMkId } = useParams();
  const navigate = useNavigate();
  const { classes, selectedPeriod } = useDosenWorkspace();

  const activeClassId = kelasMkId || classes[0]?.id || '';
  const activeClass =
    classes.find((c) => c.id === activeClassId) || classes[0] || null;

  const [design, setDesign] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [serverScores, setServerScores] = useState({});
  const [draftScores, setDraftScores] = useState({});
  const [attainment, setAttainment] = useState(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const loadGradeSheet = useCallback(async () => {
    if (!activeClassId) {
      setDesign(null);
      setParticipants([]);
      setServerScores({});
      setDraftScores({});
      setAttainment(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [designData, participantIds, gradeRows, attainmentData] =
        await Promise.all([
          getKelasRancangan(activeClassId),
          getKelasMkPeserta(activeClassId),
          getKelasMkNilai(activeClassId),
          getKelasMkCapaian(activeClassId),
        ]);

      const scoreMap = {};
      for (const row of gradeRows) {
        scoreMap[`${row.mahasiswa_id}:${row.instrumen_id}`] = formatSavedScore(
          row.nilai_mentah,
        );
      }

      setDesign(designData);
      setParticipants(participantIds);
      setServerScores(scoreMap);
      setDraftScores(scoreMap);
      setAttainment(attainmentData);
    } catch (err) {
      setError(err.message || 'Gagal memuat lembar input nilai.');
    } finally {
      setLoading(false);
    }
  }, [activeClassId]);

  useEffect(() => {
    loadGradeSheet();
  }, [loadGradeSheet]);

  const instruments = useMemo(() => {
    if (!design) return [];
    const list = [];
    for (const cpmk of design.cpmk) {
      for (const sub of cpmk.sub_cpmk) {
        for (const inst of sub.instrumen) {
          list.push({
            ...inst,
            subKode: sub.kode_sub,
            cpmkKode: cpmk.kode_cpmk,
          });
        }
      }
    }
    return list;
  }, [design]);

  const cellErrors = useMemo(() => {
    const errors = {};
    for (const studentId of participants) {
      for (const inst of instruments) {
        const key = `${studentId}:${inst.id}`;
        const raw = draftScores[key] ?? '';
        const hasSaved = key in serverScores && serverScores[key] !== '';
        const msg = validateScoreInput(raw, hasSaved);
        if (msg) {
          errors[key] = msg;
        }
      }
    }
    return errors;
  }, [draftScores, instruments, participants, serverScores]);

  const dirtyItems = useMemo(() => {
    const changes = [];
    for (const studentId of participants) {
      for (const inst of instruments) {
        const key = `${studentId}:${inst.id}`;
        const raw = (draftScores[key] ?? '').trim();
        const saved = (serverScores[key] ?? '').trim();
        if (raw === '' || cellErrors[key]) continue;

        const numDraft = Number(raw.replace(',', '.')).toFixed(2);
        const numSaved =
          saved !== '' ? Number(saved.replace(',', '.')).toFixed(2) : null;
        if (numDraft !== numSaved) {
          changes.push({
            instrumen_id: inst.id,
            mahasiswa_id: studentId,
            nilai_mentah: numDraft,
            instrumenNama: inst.nama_instrumen,
          });
        }
      }
    }
    return changes;
  }, [cellErrors, draftScores, instruments, participants, serverScores]);

  const errorCount = Object.keys(cellErrors).length;
  const mkNode = attainment?.rekap?.find((r) => r.jenis === 'Mata kuliah');
  const completeParticipants = mkNode?.mahasiswa_lengkap ?? 0;
  const totalParticipants = mkNode?.total_mahasiswa ?? participants.length;

  const handleSave = async () => {
    if (errorCount > 0 || dirtyItems.length === 0 || !activeClassId) return;
    setError('');
    setFeedback('');
    setSaving(true);
    try {
      await saveKelasMkNilai(
        activeClassId,
        dirtyItems.map(({ instrumen_id, mahasiswa_id, nilai_mentah }) => ({
          instrumen_id,
          mahasiswa_id,
          nilai_mentah,
        })),
      );
      setFeedback(`${dirtyItems.length} nilai berhasil disimpan secara atomik.`);
      await loadGradeSheet();
    } catch (err) {
      setError(err.message || 'Gagal menyimpan nilai. Tidak ada perubahan sebagian yang disimpan.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setDraftScores(serverScores);
    setFeedback('');
    setError('');
  };

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div className="flex flex-col gap-2">
          <Link
            to="/dosen"
            className="text-[13px] font-medium text-[#252525] dark:text-[#F5F5F4] hover:underline w-fit"
          >
            ‹ Dashboard Dosen
          </Link>
          <h1 className="text-[34px] font-bold leading-[41px] text-[#252525] dark:text-[#F5F5F4]">
            Input nilai
          </h1>
          {activeClass && (
            <p className="text-[16px] text-[#525252] dark:text-[#A3A3A0]">
              {activeClass.nama_mk} / {activeClass.kelas} /{' '}
              {selectedPeriod
                ? `${selectedPeriod.tahun_akademik} ${selectedPeriod.semester}`
                : ''}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          {classes.length > 1 && (
            <select
              aria-label="Pilih kelas MK"
              value={activeClassId}
              onChange={(e) => navigate(`/dosen/nilai/${e.target.value}`)}
              className="min-w-[230px] h-[38px] px-3 rounded-[7px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] text-[12px] font-medium"
            >
              {classes.map((cls) => (
                <option key={cls.id} value={cls.id}>
                  {cls.nama_mk} · {cls.kelas}
                </option>
              ))}
            </select>
          )}
          <div className="text-right">
            <p className="text-[20px] font-semibold leading-[24px] tabular-nums">
              {completeParticipants} dari {totalParticipants} peserta lengkap
            </p>
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0] mt-1">
              Berdasarkan nilai yang sudah disimpan
            </p>
          </div>
        </div>
      </div>

      {design && !design.boleh_input_nilai && (
        <div className="rounded-[10px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] px-4 py-3 flex items-center justify-between gap-4 text-[13px]">
          <span className="text-[#B55824] dark:text-[#F0C3A4]">
            {design.periode_ditutup
              ? 'Periode akademik ditutup — nilai bersifat read-only.'
              : `Rancangan belum siap dinilai: ${design.alasan_belum_siap.join('; ')}`}
          </span>
          {!design.siap_dinilai && (
            <Link
              to={`/dosen/rancangan/${design.id}`}
              className="font-medium underline shrink-0"
            >
              Lengkapi rancangan →
            </Link>
          )}
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

      <section className="bg-white dark:bg-[#1D1D1B] border border-[#DEDEDE] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-5">
        <div>
          <h2 className="text-[22px] font-semibold leading-[27px] text-[#252525] dark:text-[#F5F5F4]">
            Nilai per instrumen
          </h2>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-1">
            Skor 0–100. Tanda — berarti nilai belum diinput; angka 0 adalah skor
            sah.
          </p>
          <p className="text-[11.5px] text-[#737373] dark:text-[#A3A3A0] mt-1">
            Catatan backend: endpoint peserta kelas saat ini mengembalikan ID
            (UUID) mahasiswa sehingga nama &amp; NIM menunggu pembaruan API
            peserta.
          </p>
        </div>

        {loading ? (
          <p className="py-8 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Memuat grid penilaian...
          </p>
        ) : !activeClass ? (
          <p className="py-8 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Belum ada kelas penugasan pada periode ini.
          </p>
        ) : instruments.length === 0 ? (
          <p className="py-8 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Belum ada instrumen pada rancangan kelas ini.
          </p>
        ) : participants.length === 0 ? (
          <p className="py-8 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
            Belum ada peserta terdaftar pada kelas MK ini.
          </p>
        ) : (
          <>
            <div className="overflow-x-auto max-h-[420px] overflow-y-auto border-y border-[#E5E5E4] dark:border-[#2E2E2B]">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-white dark:bg-[#1D1D1B]">
                  <tr className="border-b border-[#E5E5E4] dark:border-[#2E2E2B]">
                    <th className="py-3 pr-4 min-w-[260px]">
                      <div className="text-[14px] font-semibold">Peserta</div>
                      <div className="text-[12px] font-normal text-[#737373] dark:text-[#A3A3A0]">
                        ID Mahasiswa
                      </div>
                    </th>
                    {instruments.map((inst) => (
                      <th key={inst.id} className="py-3 px-2 min-w-[165px]">
                        <div className="text-[14px] font-semibold truncate">
                          {inst.nama_instrumen}
                        </div>
                        <div className="text-[12px] font-normal text-[#737373] dark:text-[#A3A3A0]">
                          {Number(inst.bobot_persentase)}% · {inst.jenis_instrumen}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E4] dark:divide-[#2E2E2B]">
                  {participants.map((studentId, index) => (
                    <tr key={studentId}>
                      <td className="py-3 pr-4 align-top">
                        <div className="text-[14px] font-medium text-[#252525] dark:text-[#F5F5F4]">
                          Peserta #{index + 1}
                        </div>
                        <div className="text-[11.5px] font-mono text-[#737373] dark:text-[#A3A3A0] break-all">
                          {studentId}
                        </div>
                      </td>
                      {instruments.map((inst) => {
                        const key = `${studentId}:${inst.id}`;
                        const errId = `err-${studentId}-${inst.id}`;
                        const cellError = cellErrors[key];
                        return (
                          <td key={key} className="py-3 px-2 align-top">
                            <input
                              type="text"
                              inputMode="decimal"
                              aria-label={`Nilai ${inst.nama_instrumen} peserta ${index + 1}`}
                              aria-invalid={Boolean(cellError)}
                              aria-describedby={cellError ? errId : undefined}
                              disabled={!design?.boleh_input_nilai || saving}
                              value={draftScores[key] ?? ''}
                              placeholder="—"
                              onChange={(e) => {
                                const value = e.target.value;
                                setDraftScores((prev) => ({
                                  ...prev,
                                  [key]: value,
                                }));
                              }}
                              className={[
                                'w-[141px] h-[40px] px-3 rounded-[5px] bg-white dark:bg-[#242422] text-[14px] focus:outline-none disabled:opacity-60',
                                cellError
                                  ? 'border-2 border-[#DC2626]'
                                  : 'border border-[#DEDEDE] dark:border-[#343430] focus:border-[#777777]',
                              ].join(' ')}
                            />
                            {cellError && (
                              <p
                                id={errId}
                                className="mt-1 text-[11px] font-medium text-[#DC2626]"
                              >
                                {cellError}
                              </p>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer simpan */}
            <div className="flex items-center justify-between gap-4 pt-1">
              <div className="flex flex-col gap-1">
                <p className="text-[15px] font-medium text-[#252525] dark:text-[#F5F5F4]">
                  {errorCount > 0
                    ? `${errorCount} sel memiliki nilai tidak valid`
                    : `${dirtyItems.length} perubahan belum disimpan`}
                </p>
                <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
                  {errorCount > 0
                    ? 'Perbaiki input bertanda merah sebelum menyimpan.'
                    : dirtyItems.length > 0
                      ? dirtyItems
                          .slice(0, 3)
                          .map((i) => i.instrumenNama)
                          .join(', ')
                      : 'Semua perubahan tersinkron dengan server.'}
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {(dirtyItems.length > 0 || errorCount > 0) && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={handleReset}
                    className="h-[45px] px-4 rounded-[6px] border border-[#E5E5E5] dark:border-[#343430] text-[13px] font-medium cursor-pointer"
                  >
                    Reset
                  </button>
                )}

                <button
                  type="button"
                  disabled={
                    !design?.boleh_input_nilai ||
                    saving ||
                    errorCount > 0 ||
                    dirtyItems.length === 0
                  }
                  onClick={handleSave}
                  className="h-[45px] px-5 rounded-[6px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[14px] font-medium cursor-pointer disabled:opacity-45"
                >
                  {saving ? 'Menyimpan...' : 'Simpan perubahan'}
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
