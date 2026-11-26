import { useMemo, useState } from 'react';

function parseBidangKerja(raw) {
  if (!raw) return [];
  return raw
    .split(',')
    .map((item) => item.trim().replace(/\.+$/, '').trim())
    .filter(Boolean);
}

function StatusBadge({ status }) {
  if (status === 'Aktif') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#E6F2EE] border border-[#C6DFD7] text-[11.5px] font-semibold text-[#1A5C4D] whitespace-nowrap">
        Aktif
      </span>
    );
  }
  if (status === 'Arsip') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#EFECE4] border border-[#DDD7CA] text-[11.5px] font-semibold text-[#566B70] whitespace-nowrap">
        Arsip
      </span>
    );
  }
  return (
    <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#F7EAE1] border border-[#E8B899] text-[11.5px] font-semibold text-[#B55824] whitespace-nowrap">
      {status || 'Draft'}
    </span>
  );
}

export default function ProfilLulusanOverview({
  overview,
  activeTab: controlledTab,
  onTabChange,
  editable = false,
  draftMatrix = null,
  dirtyPlCount = 0,
  savingMatrix = false,
  onToggleMatrixLink,
  onSaveMatrix,
  onResetMatrix,
  listTopContent = null,
  renderCardActions,
  renderEditingCard,
}) {
  const [internalTab, setInternalTab] = useState('daftar');
  const activeTab = controlledTab ?? internalTab;
  const setActiveTab = onTabChange ?? setInternalTab;

  const profilList = overview?.profil_lulusan || [];
  const cplList = overview?.cpl || [];

  const cplById = useMemo(
    () => Object.fromEntries(cplList.map((cpl) => [cpl.id, cpl])),
    [cplList],
  );

  const effectiveCplIdsByPl = useMemo(() => {
    const map = {};
    for (const pl of profilList) {
      if (editable && draftMatrix && Array.isArray(draftMatrix[pl.id])) {
        map[pl.id] = draftMatrix[pl.id];
      } else {
        map[pl.id] = pl.cpl_ids || [];
      }
    }
    return map;
  }, [draftMatrix, editable, profilList]);

  const effectiveSetByPl = useMemo(() => {
    const map = {};
    for (const pl of profilList) {
      map[pl.id] = new Set(effectiveCplIdsByPl[pl.id] || []);
    }
    return map;
  }, [effectiveCplIdsByPl, profilList]);

  const totalLinks = useMemo(
    () =>
      profilList.reduce(
        (acc, pl) => acc + (effectiveCplIdsByPl[pl.id]?.length || 0),
        0,
      ),
    [effectiveCplIdsByPl, profilList],
  );

  if (!overview) {
    return (
      <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
        Data Profil Lulusan belum tersedia untuk kurikulum ini.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="min-h-[112px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Profil Lulusan
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {profilList.length}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Ditetapkan pada kurikulum
          </span>
        </div>

        <div className="min-h-[112px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Master CPL
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {cplList.length}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            CPL pendukung pada versi ini
          </span>
        </div>

        <div className="min-h-[112px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Pemetaan PL–CPL
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {totalLinks}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Tautan hubungan CPL &amp; PL
          </span>
        </div>

        <div className="min-h-[112px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Konteks Kurikulum
          </span>
          <div className="flex items-center justify-between gap-2 min-w-0">
            <span className="text-[17px] font-semibold text-[#15333A] truncate">
              {overview.kode_kurikulum}
            </span>
            <StatusBadge status={overview.status} />
          </div>
          <span className="text-[11px] text-[#7A8C90] truncate">
            {overview.nama_kurikulum}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 border-b border-[#E4DFD4] pb-3">
        <button
          type="button"
          onClick={() => setActiveTab('daftar')}
          className={[
            'h-[36px] px-4 rounded-[8px] text-[13px] font-semibold cursor-pointer transition-colors',
            activeTab === 'daftar'
              ? 'bg-[#15333A] text-white'
              : 'bg-white border border-[#E4DFD4] text-[#566B70] hover:text-[#15333A]',
          ].join(' ')}
        >
          Daftar Profil Lulusan ({profilList.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('matriks')}
          className={[
            'h-[36px] px-4 rounded-[8px] text-[13px] font-semibold cursor-pointer transition-colors',
            activeTab === 'matriks'
              ? 'bg-[#15333A] text-white'
              : 'bg-white border border-[#E4DFD4] text-[#566B70] hover:text-[#15333A]',
          ].join(' ')}
        >
          Matriks Hubungan CPL–PL ({totalLinks})
        </button>
      </div>

      {activeTab === 'daftar' ? (
        <div className="flex flex-col gap-6">
          {listTopContent}

          {profilList.length === 0 ? (
            <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
              Belum ada Profil Lulusan yang terdaftar pada kurikulum{' '}
              <strong className="text-[#15333A]">{overview.kode_kurikulum}</strong>.
            </section>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {profilList.map((pl) => {
                const customEditing = renderEditingCard?.(pl);
                if (customEditing) {
                  return (
                    <div key={pl.id} className="lg:col-span-2">
                      {customEditing}
                    </div>
                  );
                }

                const linkedCpls = (pl.cpl_ids || [])
                  .map((id) => cplById[id])
                  .filter(Boolean);
                const chips = parseBidangKerja(pl.bidang_kerja);

                return (
                  <article
                    key={pl.id}
                    className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col justify-between gap-4"
                  >
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center h-6 px-2.5 rounded-[6px] bg-[#15333A] text-white text-[11.5px] font-semibold tracking-[0.02em]">
                            {pl.kode_pl}
                          </span>
                          <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#E6F0EE] text-[#15333A] text-[11.5px] font-semibold">
                            {linkedCpls.length} CPL Pendukung
                          </span>
                        </div>
                        {renderCardActions?.(pl)}
                      </div>

                      <h2 className="text-[17px] font-semibold leading-[24px] text-[#15333A]">
                        {pl.nama_pl}
                      </h2>

                      <p className="text-[13.5px] leading-[21px] text-[#334B51]">
                        {pl.deskripsi}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-[#EFECE4] flex flex-col gap-3">
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-[#7A8C90] mb-1.5">
                          Bidang Kerja
                        </p>
                        {chips.length === 0 ? (
                          <p className="text-[12.5px] text-[#566B70]">—</p>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {chips.map((chip) => (
                              <span
                                key={chip}
                                className="inline-flex items-center px-2.5 py-1 rounded-[6px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12px] text-[#334B51]"
                              >
                                {chip}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-[0.06em] text-[#7A8C90] mb-1.5">
                          CPL Pendukung
                        </p>
                        {linkedCpls.length === 0 ? (
                          <p className="text-[12.5px] text-[#566B70]">
                            Belum ada CPL ditautkan.
                          </p>
                        ) : (
                          <div className="flex flex-wrap gap-1.5">
                            {linkedCpls.map((cpl) => (
                              <span
                                key={cpl.id}
                                title={cpl.deskripsi}
                                className="inline-flex items-center h-6 px-2.5 rounded-[6px] bg-[#E6F2EE] border border-[#C6DFD7] text-[11.5px] font-semibold text-[#1A5C4D]"
                              >
                                {cpl.kode_cpl}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-[18px] font-semibold text-[#15333A]">
                Matriks Hubungan CPL dengan Profil Lulusan
              </h2>
              <p className="text-[12.5px] text-[#566B70] mt-1">
                {editable
                  ? 'Centang pemetaan setiap CPL terhadap Profil Lulusan pada kurikulum Draft, lalu simpan perubahan.'
                  : 'Pemetaan CPL pendukung untuk setiap Profil Lulusan pada kurikulum ini.'}
              </p>
            </div>

            {editable && profilList.length > 0 && cplList.length > 0 && (
              <div className="flex items-center gap-2.5">
                {dirtyPlCount > 0 && onResetMatrix && (
                  <button
                    type="button"
                    disabled={savingMatrix}
                    onClick={onResetMatrix}
                    className="h-[36px] px-3.5 rounded-[8px] border border-[#E4DFD4] bg-white hover:bg-[#FAF8F3] text-[12.5px] font-semibold text-[#334B51] cursor-pointer disabled:opacity-50"
                  >
                    Reset
                  </button>
                )}
                <button
                  type="button"
                  disabled={savingMatrix || dirtyPlCount === 0}
                  onClick={onSaveMatrix}
                  className="h-[36px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold cursor-pointer disabled:opacity-50 transition-colors"
                >
                  {savingMatrix
                    ? 'Menyimpan...'
                    : 'Simpan Matriks PL–CPL'}
                </button>
              </div>
            )}
          </div>

          {profilList.length === 0 || cplList.length === 0 ? (
            <p className="text-[13px] text-[#566B70] py-4">
              {profilList.length === 0
                ? 'Belum ada Profil Lulusan pada kurikulum ini.'
                : 'Belum ada Master CPL pada kurikulum ini.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                    <th className="py-3 pr-4 min-w-[90px]">Kode CPL</th>
                    <th className="py-3 pr-4 min-w-[280px]">
                      Capaian Pembelajaran Lulusan
                    </th>
                    {profilList.map((pl) => (
                      <th
                        key={pl.id}
                        className="py-3 px-3 text-center min-w-[110px]"
                        title={pl.nama_pl}
                      >
                        <div className="text-[12px] font-semibold text-[#15333A]">
                          {pl.kode_pl}
                        </div>
                        <div className="text-[10.5px] font-normal text-[#7A8C90] max-w-[120px] mx-auto truncate">
                          {pl.nama_pl}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                  {cplList.map((cpl) => (
                    <tr key={cpl.id} className="hover:bg-[#FAF8F3]/70">
                      <td className="py-3 pr-4 font-semibold text-[#15333A] whitespace-nowrap align-top">
                        <div>{cpl.kode_cpl}</div>
                        <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-[#E6F0EE] text-[10.5px] font-medium text-[#15333A]">
                          {cpl.kategori}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-[12.5px] leading-[19px] text-[#334B51]">
                        {cpl.deskripsi}
                      </td>
                      {profilList.map((pl) => {
                        const checked = effectiveSetByPl[pl.id]?.has(cpl.id);
                        return (
                          <td
                            key={pl.id}
                            className="py-3 px-3 text-center align-middle"
                          >
                            {editable ? (
                              <input
                                type="checkbox"
                                checked={Boolean(checked)}
                                disabled={savingMatrix}
                                onChange={() =>
                                  onToggleMatrixLink?.(pl.id, cpl.id)
                                }
                                aria-label={`Tautkan ${cpl.kode_cpl} ke ${pl.kode_pl}`}
                                className="w-4 h-4 accent-[#15333A] cursor-pointer"
                              />
                            ) : checked ? (
                              <span
                                aria-label={`${cpl.kode_cpl} terhubung dengan ${pl.kode_pl}`}
                                className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#E6F2EE] border border-[#C6DFD7] text-[#1A5C4D] text-[12px] font-bold"
                              >
                                ✓
                              </span>
                            ) : (
                              <span
                                aria-label={`${cpl.kode_cpl} tidak terhubung dengan ${pl.kode_pl}`}
                                className="text-[#9AA8AB]"
                              >
                                —
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-[#E4DFD4] bg-[#FAF8F3] text-[12px] font-semibold text-[#15333A]">
                    <td colSpan={2} className="py-3 pr-4">
                      Total CPL Pendukung ({totalLinks} tautan)
                    </td>
                    {profilList.map((pl) => (
                      <td
                        key={pl.id}
                        className="py-3 px-3 text-center tabular-nums"
                      >
                        {effectiveCplIdsByPl[pl.id]?.length || 0}
                      </td>
                    ))}
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
