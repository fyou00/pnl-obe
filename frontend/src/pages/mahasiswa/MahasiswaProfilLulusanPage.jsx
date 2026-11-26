import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ProfilLulusanOverview from '../../components/dashboard/ProfilLulusanOverview.jsx';
import {
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';
import { getProfilLulusanRingkasan } from '../../lib/adminApi.js';

export default function MahasiswaProfilLulusanPage() {
  const { selectedPeriod } = useMahasiswaWorkspace();
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
      setError(
        err.message || 'Gagal memuat Profil Lulusan kurikulum angkatan Anda.',
      );
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#E6F0EE] border border-[#D4E3E0] text-[11.5px] font-semibold text-[#15333A]">
            <span>Mode Read-Only · Kurikulum Angkatan</span>
          </div>
          <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A] mt-2">
            Profil Lulusan
          </h1>
          <p className="text-[14px] text-[#566B70] mt-1.5">
            Target peran profesional lulusan dan pemetaan CPL pendukung pada
            kurikulum angkatan Anda.
          </p>
        </div>

        <Link
          to="/mahasiswa/capaian"
          className="h-[38px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold inline-flex items-center transition-colors shrink-0"
        >
          Lihat Capaian CPL Saya →
        </Link>
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
