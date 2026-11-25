import { useCallback, useEffect, useState } from 'react';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import {
  getMatriksMk,
  listCpl,
  listPaketMk,
  replaceMatriksMk,
} from '../../lib/adminApi.js';

export default function AdminMatriksPage() {
  const {
    curricula,
    selectedCurriculumId,
    setSelectedCurriculumId,
    selectedCurriculum,
  } = useAdminWorkspace();

  const [courses, setCourses] = useState([]);
  const [cpls, setCpls] = useState([]);
  const [selectedMkId, setSelectedMkId] = useState('');
  const [selectedMap, setSelectedMap] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingMatrix, setLoadingMatrix] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const isDraft = selectedCurriculum?.status === 'Draft';

  const loadCurriculumItems = useCallback(async () => {
    if (!selectedCurriculumId) {
      setCourses([]);
      setCpls([]);
      setSelectedMkId('');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [coursesData, cplsData] = await Promise.all([
        listPaketMk(selectedCurriculumId, { limit: 100 }),
        listCpl(selectedCurriculumId, { limit: 100 }),
      ]);
      setCourses(coursesData);
      setCpls(cplsData);
      setSelectedMkId((prev) =>
        prev && coursesData.some((c) => c.id === prev)
          ? prev
          : coursesData[0]?.id || '',
      );
    } catch (err) {
      setError(err.message || 'Gagal memuat mata kuliah dan CPL kurikulum.');
    } finally {
      setLoading(false);
    }
  }, [selectedCurriculumId]);

  useEffect(() => {
    loadCurriculumItems();
  }, [loadCurriculumItems]);

  const loadMatrix = useCallback(async () => {
    if (!selectedCurriculumId || !selectedMkId) {
      setSelectedMap({});
      return;
    }
    setLoadingMatrix(true);
    setError('');
    setFeedback('');
    try {
      const links = await getMatriksMk(selectedCurriculumId, selectedMkId);
      const next = {};
      for (const link of links) {
        next[link.cpl_id] =
          link.urutan_rps !== null && link.urutan_rps !== undefined
            ? String(link.urutan_rps)
            : '';
      }
      setSelectedMap(next);
    } catch (err) {
      setError(err.message || 'Gagal memuat pembebanan CPL.');
    } finally {
      setLoadingMatrix(false);
    }
  }, [selectedCurriculumId, selectedMkId]);

  useEffect(() => {
    loadMatrix();
  }, [loadMatrix]);

  const toggleCpl = (cplId) => {
    if (!isDraft) return;
    setSelectedMap((prev) => {
      const copy = { ...prev };
      if (cplId in copy) {
        delete copy[cplId];
      } else {
        copy[cplId] = '';
      }
      return copy;
    });
  };

  const setOrder = (cplId, value) => {
    setSelectedMap((prev) => ({
      ...prev,
      [cplId]: value,
    }));
  };

  const handleSave = async () => {
    if (!isDraft || !selectedCurriculumId || !selectedMkId) return;
    setError('');
    setFeedback('');
    setSaving(true);
    try {
      const items = Object.entries(selectedMap).map(([cpl_id, urutan]) => ({
        cpl_id,
        urutan_rps: urutan === '' ? null : Number(urutan),
      }));
      await replaceMatriksMk(selectedCurriculumId, selectedMkId, items);
      setFeedback('Matriks pembebanan CPL–MK berhasil disimpan.');
    } catch (err) {
      setError(err.message || 'Gagal menyimpan matriks pembebanan.');
    } finally {
      setSaving(false);
    }
  };

  const activeCourse = courses.find((c) => c.id === selectedMkId);

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#252525] dark:text-[#F5F5F4]">
            Matriks pembebanan CPL–MK
          </h1>
          <p className="text-[14px] text-[#737373] dark:text-[#A3A3A0] mt-2">
            Tautkan CPL ke mata kuliah dalam versi kurikulum yang sama. Hanya
            kurikulum Draft yang dapat diubah.
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

      {selectedCurriculum && !isDraft && (
        <div className="rounded-[10px] bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] px-4 py-3 text-[13px] text-[#525252] dark:text-[#D4D4D0]">
          Kurikulum <strong>{selectedCurriculum.nama}</strong> berstatus{' '}
          <strong>{selectedCurriculum.status}</strong> (read-only).
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

      <div className="grid grid-cols-[320px_1fr] gap-6 items-start">
        <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-5 flex flex-col gap-3">
          <h2 className="text-[16px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
            Mata Kuliah Paket
          </h2>

          {loading ? (
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Memuat...
            </p>
          ) : courses.length === 0 ? (
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Belum ada mata kuliah pada versi kurikulum ini.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {courses.map((course) => {
                const active = course.id === selectedMkId;
                return (
                  <button
                    key={course.id}
                    type="button"
                    onClick={() => setSelectedMkId(course.id)}
                    className={[
                      'text-left px-3 py-2.5 rounded-[7px] text-[13px] cursor-pointer transition-colors',
                      active
                        ? 'bg-[#F0F0EF] dark:bg-[#2A2A27] border border-[#E5E5E5] dark:border-[#343430] font-semibold'
                        : 'hover:bg-[#F5F5F4] dark:hover:bg-[#2A2A27]/50 text-[#525252] dark:text-[#A3A3A0]',
                    ].join(' ')}
                  >
                    <div className="truncate">{course.nama_mk}</div>
                    <div className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                      Semester {course.semester} · {course.sks} SKS
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                {activeCourse
                  ? `CPL untuk ${activeCourse.nama_mk}`
                  : 'Pilih mata kuliah'}
              </h2>
              <p className="text-[12px] text-[#737373] dark:text-[#A3A3A0] mt-1">
                {Object.keys(selectedMap).length} dari {cpls.length} CPL
                dibebankan
              </p>
            </div>

            {isDraft && activeCourse && (
              <button
                type="button"
                disabled={saving || loadingMatrix}
                onClick={handleSave}
                className="h-[38px] px-4 rounded-[7px] bg-[#252525] dark:bg-[#F5F5F4] text-white dark:text-[#252525] text-[12px] font-medium cursor-pointer disabled:opacity-60"
              >
                {saving ? 'Menyimpan...' : 'Simpan pembebanan'}
              </button>
            )}
          </div>

          {!activeCourse ? (
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Pilih mata kuliah di sebelah kiri.
            </p>
          ) : loadingMatrix ? (
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Memuat pembebanan CPL...
            </p>
          ) : cpls.length === 0 ? (
            <p className="text-[13px] text-[#737373] dark:text-[#A3A3A0]">
              Belum ada Master CPL pada versi kurikulum ini.
            </p>
          ) : (
            <div className="divide-y divide-[#E5E5E5] dark:divide-[#2E2E2B]">
              {cpls.map((cpl) => {
                const checked = cpl.id in selectedMap;
                return (
                  <div
                    key={cpl.id}
                    className="py-3.5 flex items-start justify-between gap-4"
                  >
                    <label className="flex items-start gap-3 flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={!isDraft}
                        onChange={() => toggleCpl(cpl.id)}
                        className="mt-1"
                      />
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[13.5px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
                          {cpl.kode_cpl} ({cpl.kategori})
                        </span>
                        <span className="text-[12.5px] text-[#525252] dark:text-[#A3A3A0]">
                          {cpl.deskripsi}
                        </span>
                      </div>
                    </label>

                    {checked && (
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[11px] text-[#737373] dark:text-[#A3A3A0]">
                          Urutan RPS
                        </span>
                        <input
                          type="number"
                          min={1}
                          disabled={!isDraft}
                          value={selectedMap[cpl.id]}
                          onChange={(e) => setOrder(cpl.id, e.target.value)}
                          placeholder="—"
                          className="w-16 h-[32px] px-2 rounded-[7px] border border-[#E5E5E5] dark:border-[#343430] bg-white dark:bg-[#242422] text-[12px] text-center"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
