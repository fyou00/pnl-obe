import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/auth/ProtectedRoute.jsx';
import AdminLayout from './components/dashboard/AdminLayout.jsx';
import DosenLayout from './components/dashboard/DosenLayout.jsx';
import MahasiswaLayout from './components/dashboard/MahasiswaLayout.jsx';
import { AdminWorkspaceProvider } from './context/AdminWorkspaceContext.jsx';
import { DosenWorkspaceProvider } from './context/DosenWorkspaceContext.jsx';
import { MahasiswaWorkspaceProvider } from './context/MahasiswaWorkspaceContext.jsx';
import AdminAngkatanKelasPage from './pages/admin/AdminAngkatanKelasPage.jsx';
import AdminCplPage from './pages/admin/AdminCplPage.jsx';
import AdminDashboardPage from './pages/admin/AdminDashboardPage.jsx';
import AdminKurikulumPage from './pages/admin/AdminKurikulumPage.jsx';
import AdminLaporanPage from './pages/admin/AdminLaporanPage.jsx';
import AdminMataKuliahPage from './pages/admin/AdminMataKuliahPage.jsx';
import AdminMatriksPage from './pages/admin/AdminMatriksPage.jsx';
import AdminPaketPenugasanPage from './pages/admin/AdminPaketPenugasanPage.jsx';
import AdminPeriodePage from './pages/admin/AdminPeriodePage.jsx';
import DosenCapaianPage from './pages/dosen/DosenCapaianPage.jsx';
import DosenDashboardPage from './pages/dosen/DosenDashboardPage.jsx';
import DosenInputNilaiPage from './pages/dosen/DosenInputNilaiPage.jsx';
import DosenRancanganPage from './pages/dosen/DosenRancanganPage.jsx';
import LandingPage from './pages/LandingPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import MahasiswaCapaianPage from './pages/mahasiswa/MahasiswaCapaianPage.jsx';
import MahasiswaDashboardPage from './pages/mahasiswa/MahasiswaDashboardPage.jsx';
import MahasiswaMataKuliahPage from './pages/mahasiswa/MahasiswaMataKuliahPage.jsx';
import MahasiswaRincianPage from './pages/mahasiswa/MahasiswaRincianPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/ruang-kerja" element={<Navigate to="/mahasiswa" replace />} />

      <Route
        path="/mahasiswa"
        element={
          <ProtectedRoute allowedRoles={['Mahasiswa']}>
            <MahasiswaWorkspaceProvider>
              <MahasiswaLayout />
            </MahasiswaWorkspaceProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<MahasiswaDashboardPage />} />
        <Route path="mata-kuliah" element={<MahasiswaMataKuliahPage />} />
        <Route path="rincian" element={<MahasiswaRincianPage />} />
        <Route path="capaian" element={<MahasiswaCapaianPage />} />
      </Route>

      <Route
        path="/dosen"
        element={
          <ProtectedRoute allowedRoles={['Dosen']}>
            <DosenWorkspaceProvider>
              <DosenLayout />
            </DosenWorkspaceProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<DosenDashboardPage />} />
        <Route path="rancangan" element={<DosenRancanganPage />} />
        <Route path="rancangan/:rancanganId" element={<DosenRancanganPage />} />
        <Route path="nilai" element={<DosenInputNilaiPage />} />
        <Route path="nilai/:kelasMkId" element={<DosenInputNilaiPage />} />
        <Route path="capaian" element={<DosenCapaianPage />} />
      </Route>

      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['Admin']}>
            <AdminWorkspaceProvider>
              <AdminLayout />
            </AdminWorkspaceProvider>
          </ProtectedRoute>
        }
      >
        <Route index element={<AdminDashboardPage />} />
        <Route path="kurikulum" element={<AdminKurikulumPage />} />
        <Route path="cpl" element={<AdminCplPage />} />
        <Route path="mata-kuliah" element={<AdminMataKuliahPage />} />
        <Route path="matriks" element={<AdminMatriksPage />} />
        <Route path="periode" element={<AdminPeriodePage />} />
        <Route path="angkatan" element={<AdminAngkatanKelasPage />} />
        <Route path="paket" element={<AdminPaketPenugasanPage />} />
        <Route path="pengguna" element={<Navigate to="/admin" replace />} />
        <Route path="laporan" element={<AdminLaporanPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
