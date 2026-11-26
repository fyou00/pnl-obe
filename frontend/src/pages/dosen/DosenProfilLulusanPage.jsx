import { useCallback, useEffect, useState } from 'react';
import ProfilLulusanOverview from '../../components/dashboard/ProfilLulusanOverview.jsx';
import {
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import { getProfilLulusanRingkasan } from '../../lib/adminApi.js';

export default function DosenProfilLulusanPage() {
  const { selectedPeriod } = useDosenWorkspace();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getProfilLulusanRingkasan();
      setOverview(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat Profil Lulusan program studi.');
      setOverview(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div>
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#E6F0EE] border border-[#D4E3E0] text-[11.5px] font-semibold text-[#15333A]">
          <span>Mode Read-Only · Referensi Kurikulum</span>
        </div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A] mt-2">
          Profil Lulusan &amp; Matriks PL–CPL
        </h1>
        <p className="text-[14px] text-[#566B70] mt-1.5">
          Gambaran kompetensi lulusan program studi dan keterkaitan tiap CPL
          pendukung sebagai acuan penyusunan CPMK/RPS.
        </p>
      </div>

      <LockedPeriodBanner period={selectedPeriod} />

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
        >
          {error}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton variant="cards" />
      ) : (
        <ProfilLulusanOverview overview={overview} />
      )}
    </div>
  );
}
