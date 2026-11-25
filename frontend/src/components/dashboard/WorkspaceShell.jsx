import AdminSidebar from './AdminSidebar.jsx';
import DashboardTopbar from './DashboardTopbar.jsx';

export default function WorkspaceShell({
  navGroups,
  showPeriodSelector = false,
  periods = [],
  selectedPeriodId = '',
  onSelectPeriod,
  selectedPeriod = null,
  leftContextLabel = '',
  topContextBadge = null,
  children,
}) {
  return (
    <div className="min-h-screen w-full flex bg-[#FAF8F3] text-[#15333A]">
      <AdminSidebar navGroups={navGroups} />

      <div className="flex-1 min-w-0 flex flex-col">
        <DashboardTopbar
          showPeriodSelector={showPeriodSelector}
          periods={periods}
          selectedPeriodId={selectedPeriodId}
          onSelectPeriod={onSelectPeriod}
          selectedPeriod={selectedPeriod}
          leftContextLabel={leftContextLabel}
          topContextBadge={topContextBadge}
        />

        <main className="flex-1 px-8 py-8">{children}</main>
      </div>
    </div>
  );
}
