import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';

export function getHomeRouteForRole(role) {
  if (role === 'Admin') return '/admin';
  if (role === 'Dosen') return '/dosen';
  return '/ruang-kerja';
}

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, status } = useAuth();

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-[#F5F5F4] dark:bg-[#141413] text-[#252525] dark:text-[#F5F5F4] flex items-center justify-center">
        <div className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] px-6 py-4 text-[13px] text-[#737373] dark:text-[#A3A3A0]">
          Memverifikasi sesi pengguna...
        </div>
      </div>
    );
  }

  if (status !== 'authenticated' || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />;
  }

  return children;
}
