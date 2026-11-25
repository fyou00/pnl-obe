import { Outlet } from 'react-router-dom';
import { useDosenWorkspace } from '../../context/DosenWorkspaceContext.jsx';
import WorkspaceShell from './WorkspaceShell.jsx';

export const DOSEN_NAV_GROUPS = [
  {
    label: 'RUANG DOSEN',
    items: [
      { to: '/dosen', label: 'Dashboard', end: true },
      { to: '/dosen/rancangan', label: 'Rancangan penilaian' },
      { to: '/dosen/nilai', label: 'Input nilai' },
      { to: '/dosen/capaian', label: 'Capaian kelas' },
    ],
  },
];

export default function DosenLayout() {
  const {
    periods,
    selectedPeriodId,
    setSelectedPeriodId,
    selectedPeriod,
  } = useDosenWorkspace();

  return (
    <WorkspaceShell
      navGroups={DOSEN_NAV_GROUPS}
      showPeriodSelector
      periods={periods}
      selectedPeriodId={selectedPeriodId}
      onSelectPeriod={setSelectedPeriodId}
      selectedPeriod={selectedPeriod}
    >
      <Outlet />
    </WorkspaceShell>
  );
}
