import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { listKurikulum, listPeriode } from '../lib/adminApi.js';
import { useAuth } from './AuthContext.jsx';

const AdminWorkspaceContext = createContext(null);

export function AdminWorkspaceProvider({ children }) {
  const { user, status } = useAuth();
  const [periods, setPeriods] = useState([]);
  const [curricula, setCurricula] = useState([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState('');
  const [selectedCurriculumId, setSelectedCurriculumId] = useState('');
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [metaError, setMetaError] = useState('');

  const refreshPeriods = useCallback(async () => {
    const data = await listPeriode({ limit: 100 });
    setPeriods(data);
    setSelectedPeriodId((prev) => {
      if (prev && data.some((item) => item.id === prev)) return prev;
      const openPeriod = data.find((item) => item.status === 'Dibuka');
      return openPeriod?.id || data[0]?.id || '';
    });
    return data;
  }, []);

  const refreshCurricula = useCallback(async () => {
    const data = await listKurikulum({ limit: 100 });
    setCurricula(data);
    setSelectedCurriculumId((prev) => {
      if (prev && data.some((item) => item.id === prev)) return prev;
      const activeCurriculum = data.find((item) => item.status === 'Aktif');
      return activeCurriculum?.id || data[0]?.id || '';
    });
    return data;
  }, []);

  const loadWorkspaceMeta = useCallback(async () => {
    if (status !== 'authenticated' || user?.role !== 'Admin') {
      setLoadingMeta(false);
      return;
    }
    setLoadingMeta(true);
    setMetaError('');
    try {
      await Promise.all([refreshPeriods(), refreshCurricula()]);
    } catch (err) {
      setMetaError(err.message || 'Gagal memuat konteks periode dan kurikulum.');
    } finally {
      setLoadingMeta(false);
    }
  }, [refreshCurricula, refreshPeriods, status, user?.role]);

  useEffect(() => {
    loadWorkspaceMeta();
  }, [loadWorkspaceMeta]);

  const selectedPeriod = useMemo(
    () => periods.find((item) => item.id === selectedPeriodId) || null,
    [periods, selectedPeriodId],
  );

  const selectedCurriculum = useMemo(
    () => curricula.find((item) => item.id === selectedCurriculumId) || null,
    [curricula, selectedCurriculumId],
  );

  return (
    <AdminWorkspaceContext.Provider
      value={{
        periods,
        curricula,
        selectedPeriodId,
        setSelectedPeriodId,
        selectedPeriod,
        selectedCurriculumId,
        setSelectedCurriculumId,
        selectedCurriculum,
        loadingMeta,
        metaError,
        refreshPeriods,
        refreshCurricula,
        reloadWorkspaceMeta: loadWorkspaceMeta,
      }}
    >
      {children}
    </AdminWorkspaceContext.Provider>
  );
}

export function useAdminWorkspace() {
  const ctx = useContext(AdminWorkspaceContext);
  if (!ctx) {
    throw new Error(
      'useAdminWorkspace harus digunakan di dalam AdminWorkspaceProvider',
    );
  }
  return ctx;
}
