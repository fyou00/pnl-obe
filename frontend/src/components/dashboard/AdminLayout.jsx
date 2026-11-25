import { Outlet } from 'react-router-dom';
import { useAdminWorkspace } from '../../context/AdminWorkspaceContext.jsx';
import WorkspaceShell from './WorkspaceShell.jsx';

export default function AdminLayout() {
  const {
    periods,
    selectedPeriodId,
    setSelectedPeriodId,
    selectedPeriod,
  } = useAdminWorkspace();

  return (
    <WorkspaceShell
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
