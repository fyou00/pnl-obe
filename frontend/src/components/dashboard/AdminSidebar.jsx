import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';

export const ADMIN_NAV_GROUPS = [
  {
    label: 'RUANG ADMIN',
    items: [{ to: '/admin', label: 'Dashboard', end: true }],
  },
  {
    label: 'KURIKULUM',
    items: [
      { to: '/admin/kurikulum', label: 'Versi kurikulum' },
      { to: '/admin/cpl', label: 'Master CPL' },
      { to: '/admin/mata-kuliah', label: 'Mata kuliah' },
      { to: '/admin/matriks', label: 'Matriks pembebanan' },
    ],
  },
  {
    label: 'AKADEMIK',
    items: [
      { to: '/admin/periode', label: 'Periode akademik' },
      { to: '/admin/angkatan', label: 'Angkatan dan kelas' },
      { to: '/admin/paket', label: 'Paket dan penugasan' },
    ],
  },
  {
    label: 'PENGELOLAAN',
    items: [
      { to: '/admin/pengguna', label: 'Pengguna' },
      { to: '/admin/laporan', label: 'Laporan OBE' },
    ],
  },
];

function getRoleCaption(role) {
  if (role === 'Admin') return 'Kaprodi / Admin';
  return role || 'Pengguna';
}

export default function AdminSidebar({ navGroups = ADMIN_NAV_GROUPS }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initial = (user?.nama || user?.role || 'A').trim().charAt(0).toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside className="w-[240px] shrink-0 min-h-screen sticky top-0 max-h-screen bg-white dark:bg-[#1D1D1B] border-r border-[#E5E5E5] dark:border-[#2E2E2B] flex flex-col justify-between">
      <div className="flex flex-col min-h-0 flex-1">
        <div className="px-[26px] pt-[30px] pb-[28px]">
          <p className="text-[22px] font-bold leading-[27px] text-[#252525] dark:text-[#F5F5F4]">
            PNL / OBE
          </p>
          <p className="text-[12px] leading-[15px] text-[#737373] dark:text-[#A3A3A0] mt-1">
            Pengukuran Capaian
          </p>
        </div>

        <div
          className="mx-6 h-px bg-[#E5E5E5] dark:bg-[#2E2E2B]"
          aria-hidden="true"
        />

        <nav
          aria-label="Navigasi workspace"
          className="px-4 py-6 flex-1 overflow-y-auto flex flex-col gap-6"
        >
          {navGroups.map((group) => (
            <div key={group.label} className="flex flex-col gap-1">
              <p className="px-[14px] mb-1.5 text-[10px] font-semibold tracking-[0.04em] leading-[12px] text-[#737373] dark:text-[#A3A3A0]">
                {group.label}
              </p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    isActive
                      ? 'h-[42px] px-[14px] rounded-[7px] flex items-center bg-[#F0F0EF] dark:bg-[#2A2A27] border border-[#E5E5E5] dark:border-[#343430] text-[13px] font-semibold text-[#252525] dark:text-[#F5F5F4]'
                      : 'h-[36px] px-[14px] rounded-[7px] flex items-center text-[13px] font-normal text-[#737373] dark:text-[#A3A3A0] hover:text-[#252525] dark:hover:text-[#F5F5F4] hover:bg-[#F5F5F4]/60 dark:hover:bg-[#2A2A27]/50 transition-colors'
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </div>

      <div>
        <div
          className="mx-6 h-px bg-[#E5E5E5] dark:bg-[#2E2E2B]"
          aria-hidden="true"
        />
        <div className="px-6 py-6 flex items-start gap-3">
          <div className="w-[38px] h-[38px] rounded-full bg-[#F0F0EF] dark:bg-[#2A2A27] flex items-center justify-center text-[13px] font-medium text-[#252525] dark:text-[#F5F5F4] shrink-0">
            {initial}
          </div>
          <div className="min-w-0 flex-1 flex flex-col">
            <p className="text-[13px] leading-[16px] text-[#252525] dark:text-[#F5F5F4] truncate">
              {user?.nama || 'Nama pengguna'}
            </p>
            <p className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0] mt-[6px]">
              {getRoleCaption(user?.role)}
            </p>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-2 self-start text-[12px] font-medium leading-[15px] text-[#252525] dark:text-[#F5F5F4] hover:underline cursor-pointer"
            >
              Keluar
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
