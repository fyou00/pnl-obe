import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import ChangePasswordModal from '../auth/ChangePasswordModal.jsx';
import AnimatedNavIcon from '../icons/AnimatedNavIcon.jsx';

export const ADMIN_NAV_GROUPS = [
  {
    label: 'RUANG ADMIN',
    items: [
      { to: '/admin', label: 'Dashboard', end: true, icon: 'dashboard' },
    ],
  },
  {
    label: 'KURIKULUM',
    items: [
      { to: '/admin/kurikulum', label: 'Versi Kurikulum', icon: 'kurikulum' },
      { to: '/admin/profil-lulusan', label: 'Profil Lulusan', icon: 'profil-lulusan' },
      { to: '/admin/cpl', label: 'Master CPL', icon: 'cpl' },
      { to: '/admin/mata-kuliah', label: 'Mata Kuliah Paket', icon: 'mata-kuliah' },
      { to: '/admin/matriks', label: 'Matriks Pembebanan', icon: 'matriks' },
    ],
  },
  {
    label: 'AKADEMIK',
    items: [
      { to: '/admin/periode', label: 'Periode Akademik', icon: 'periode' },
      { to: '/admin/angkatan', label: 'Angkatan & Roster', icon: 'roster' },
      { to: '/admin/paket', label: 'Paket & Penugasan', icon: 'paket' },
    ],
  },
  {
    label: 'PENGELOLAAN',
    items: [
      { to: '/admin/pengguna', label: 'Manajemen Pengguna', icon: 'pengguna' },
      { to: '/admin/laporan', label: 'Laporan & Audit Log', icon: 'laporan' },
    ],
  },
];

function getRoleCaption(role) {
  if (role === 'Admin') return 'Kaprodi / Admin';
  if (role === 'Dosen') return 'Dosen Pengampu';
  return role || 'Pengguna';
}

export default function AdminSidebar({ navGroups = ADMIN_NAV_GROUPS }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  const initial = (user?.nama || user?.role || 'A')
    .trim()
    .charAt(0)
    .toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside className="w-[240px] shrink-0 min-h-screen sticky top-0 max-h-screen bg-white border-r border-[#E4DFD4] flex flex-col justify-between">
      <div className="flex flex-col min-h-0 flex-1">
        <div className="px-6 pt-6 pb-5 flex items-center gap-3">
          <span className="w-8 h-8 rounded-[8px] bg-[#15333A] flex items-center justify-center text-[#FAF8F3] font-bold text-[15px] leading-none shrink-0">
            O
          </span>
          <div className="min-w-0">
            <p className="text-[17px] font-bold leading-[20px] tracking-[-0.01em] text-[#15333A]">
              PNL OBE
            </p>
            <p className="text-[11px] leading-[14px] text-[#566B70] mt-0.5 truncate">
              Pengukuran Capaian
            </p>
          </div>
        </div>

        <div className="mx-6 h-px bg-[#EFECE4]" aria-hidden="true" />

        <nav
          aria-label="Navigasi workspace"
          className="px-3.5 py-5 flex-1 overflow-y-auto flex flex-col gap-5"
        >
          {navGroups.map((group) => (
            <div key={group.label} className="flex flex-col gap-1">
              <p className="px-3 mb-1 text-[10.5px] font-bold tracking-[0.08em] leading-[14px] text-[#7A8C90]">
                {group.label}
              </p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      'obe-nav-trigger relative h-[38px] px-3 rounded-[8px] flex items-center gap-2.5 text-[13px] transition-colors',
                      isActive
                        ? 'bg-[#E6F0EE] border border-[#D4E3E0] font-semibold text-[#15333A]'
                        : 'font-medium text-[#566B70] hover:text-[#15333A] hover:bg-[#FAF8F3]',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span
                          className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-[#CC6E38]"
                          aria-hidden="true"
                        />
                      )}
                      <AnimatedNavIcon
                        name={item.icon || 'dashboard'}
                        active={isActive}
                        size={17}
                      />
                      <span className="truncate">{item.label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </div>

      <div>
        <div className="mx-6 h-px bg-[#EFECE4]" aria-hidden="true" />
        <div className="px-5 py-5 flex items-start gap-3">
          <div className="w-[38px] h-[38px] rounded-full bg-[#E6F0EE] border border-[#D4E3E0] flex items-center justify-center text-[13px] font-semibold text-[#15333A] shrink-0">
            {initial}
          </div>
          <div className="min-w-0 flex-1 flex flex-col">
            <p className="text-[13px] font-semibold leading-[17px] text-[#15333A] truncate">
              {user?.nama || 'Nama pengguna'}
            </p>
            <p className="text-[11px] leading-[14px] text-[#566B70] mt-0.5">
              {getRoleCaption(user?.role)}
            </p>
            <div className="mt-2 flex items-center gap-3 flex-wrap">
              <button
                type="button"
                onClick={() => setPasswordModalOpen(true)}
                className="obe-nav-trigger inline-flex items-center gap-1.5 text-[12px] font-semibold leading-[15px] text-[#566B70] hover:text-[#15333A] transition-colors cursor-pointer"
              >
                <AnimatedNavIcon name="key" size={14} />
                <span>Ganti Sandi</span>
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="obe-nav-trigger inline-flex items-center gap-1.5 text-[12px] font-semibold leading-[15px] text-[#15333A] hover:text-[#CC6E38] transition-colors cursor-pointer"
              >
                <AnimatedNavIcon name="logout" size={14} />
                <span>Keluar</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <ChangePasswordModal
        open={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
      />
    </aside>
  );
}
