import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  listMahasiswaKelasMk,
  listMahasiswaPeriode,
} from '../lib/mahasiswaApi.js';
import { useAuth } from './AuthContext.jsx';

const MahasiswaWorkspaceContext = createContext(null);

export function MahasiswaWorkspaceProvider({ children }) {
  const { user, status } = useAuth();
  const [periods, setPeriods] = useState([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState('');
  const [classes, setClasses] = useState([]);
  const [loadingPeriods, setLoadingPeriods] = useState(true);
  const [loadingClasses, setLoadingClasses] = useState(false);
  const [workspaceError, setWorkspaceError] = useState('');

  const refreshPeriods = useCallback(async () => {
    if (status !== 'authenticated' || user?.role !== 'Mahasiswa') {
      setPeriods([]);
      setLoadingPeriods(false);
      return [];
    }
    setLoadingPeriods(true);
    setWorkspaceError('');
    try {
      const data = await listMahasiswaPeriode();
      setPeriods(data);
      setSelectedPeriodId((prev) => {
        if (prev && data.some((p) => p.periode_id === prev)) {
          return prev;
        }
        const openPeriod = data.find((p) => p.status_periode === 'Dibuka');
        return openPeriod?.periode_id || data[0]?.periode_id || '';
      });
      return data;
    } catch (err) {
      setWorkspaceError(
        err.message || 'Gagal memuat daftar periode akademik Mahasiswa.',
      );
      return [];
    } finally {
      setLoadingPeriods(false);
    }
  }, [status, user?.role]);

  useEffect(() => {
    refreshPeriods();
  }, [refreshPeriods]);

  const selectedPeriod = useMemo(
    () => periods.find((p) => p.periode_id === selectedPeriodId) || null,
    [periods, selectedPeriodId],
  );

  const isTikOrInactive = useMemo(() => {
    if (!selectedPeriod) return false;
    return (
      selectedPeriod.kode_kelas === 'K' ||
      selectedPeriod.status_mahasiswa !== 'Aktif'
    );
  }, [selectedPeriod]);

  const refreshClasses = useCallback(async () => {
    if (
      status !== 'authenticated' ||
      user?.role !== 'Mahasiswa' ||
      !selectedPeriodId ||
      isTikOrInactive
    ) {
      setClasses([]);
      return [];
    }
    setLoadingClasses(true);
    setWorkspaceError('');
    try {
      const data = await listMahasiswaKelasMk(selectedPeriodId, { limit: 100 });
      setClasses(data);
      return data;
    } catch (err) {
      setWorkspaceError(
        err.message || 'Gagal memuat mata kuliah paket periode terpilih.',
      );
      setClasses([]);
      return [];
    } finally {
      setLoadingClasses(false);
    }
  }, [isTikOrInactive, selectedPeriodId, status, user?.role]);

  useEffect(() => {
    refreshClasses();
  }, [refreshClasses]);

  const refreshMahasiswaWorkspace = useCallback(async () => {
    await refreshPeriods();
    await refreshClasses();
  }, [refreshClasses, refreshPeriods]);

  return (
    <MahasiswaWorkspaceContext.Provider
      value={{
        periods,
        selectedPeriodId,
        setSelectedPeriodId,
        selectedPeriod,
        isTikOrInactive,
        classes,
        loadingWorkspace: loadingPeriods || loadingClasses,
        workspaceError,
        refreshMahasiswaWorkspace,
      }}
    >
      {children}
    </MahasiswaWorkspaceContext.Provider>
  );
}

export function useMahasiswaWorkspace() {
  const ctx = useContext(MahasiswaWorkspaceContext);
  if (!ctx) {
    throw new Error(
      'useMahasiswaWorkspace harus digunakan di dalam MahasiswaWorkspaceProvider',
    );
  }
  return ctx;
}
