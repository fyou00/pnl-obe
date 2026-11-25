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
  children,
}) {
  return (
    <div className="min-h-screen w-full flex bg-[#F5F5F4] dark:bg-[#141413] text-[#252525] dark:text-[#F5F5F4]">
      <AdminSidebar navGroups={navGroups} />

      <div className="flex-1 min-w-0 flex flex-col">
        <DashboardTopbar
          showPeriodSelector={showPeriodSelector}
          periods={periods}
          selectedPeriodId={selectedPeriodId}
          onSelectPeriod={onSelectPeriod}
          selectedPeriod={selectedPeriod}
          leftContextLabel={leftContextLabel}
        />

        <main className="flex-1 px-8 py-8">{children}</main>
      </div>
    </div>
  );
}
