import { Outlet } from 'react-router-dom';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';
import WorkspaceShell from './WorkspaceShell.jsx';

export const MAHASISWA_NAV_GROUPS = [
  {
    label: 'RUANG MAHASISWA',
    items: [
      { to: '/mahasiswa', label: 'Dashboard', end: true, icon: 'dashboard' },
      {
        to: '/mahasiswa/mata-kuliah',
        label: 'Mata Kuliah Saya',
        icon: 'mata-kuliah',
      },
      { to: '/mahasiswa/rincian', label: 'Rincian Nilai', icon: 'rincian' },
      { to: '/mahasiswa/capaian', label: 'Capaian CPL', icon: 'capaian' },
    ],
  },
];

export default function MahasiswaLayout() {
  const {
    periods,
    selectedPeriodId,
    setSelectedPeriodId,
    selectedPeriod,
    isTikOrInactive,
  } = useMahasiswaWorkspace();

  const topContextBadge = selectedPeriod ? (
    <span
      className={[
        'inline-flex items-center h-7 px-2.5 rounded-full text-[11.5px] font-semibold whitespace-nowrap',
        isTikOrInactive
          ? 'bg-[#F7EAE1] border border-[#E8B899] text-[#B55824]'
          : 'bg-[#E6F0EE] border border-[#D4E3E0] text-[#15333A]',
      ].join(' ')}
    >
      {selectedPeriod.kelas} · {selectedPeriod.status_mahasiswa}
    </span>
  ) : null;

  return (
    <WorkspaceShell
      navGroups={MAHASISWA_NAV_GROUPS}
      showPeriodSelector
      periods={periods}
      selectedPeriodId={selectedPeriodId}
      onSelectPeriod={setSelectedPeriodId}
      selectedPeriod={selectedPeriod}
      topContextBadge={topContextBadge}
    >
      <Outlet />
    </WorkspaceShell>
  );
}
