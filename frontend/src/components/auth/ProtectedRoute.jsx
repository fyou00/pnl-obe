import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { AccessDeniedState } from '../states/SystemStates.jsx';

export function getHomeRouteForRole(role) {
  if (role === 'Admin') return '/admin';
  if (role === 'Dosen') return '/dosen';
  return '/mahasiswa';
}

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, status } = useAuth();

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-[#FAF8F3] text-[#15333A] flex items-center justify-center px-6">
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] px-6 py-4 shadow-[0_8px_24px_rgba(21,51,58,0.06)] text-[13px] font-medium text-[#566B70]">
          Memverifikasi sesi pengguna...
        </div>
      </div>
    );
  }

  if (status !== 'authenticated' || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <AccessDeniedState
        role={user.role}
        homePath={getHomeRouteForRole(user.role)}
      />
    );
  }

  return children;
}
