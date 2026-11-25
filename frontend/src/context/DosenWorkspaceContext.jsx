import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { listKelasMk } from '../lib/adminApi.js';
import { listRancangan } from '../lib/dosenApi.js';
import { useAuth } from './AuthContext.jsx';

const DosenWorkspaceContext = createContext(null);

export function DosenWorkspaceProvider({ children }) {
  const { user, status } = useAuth();
  const [allDesigns, setAllDesigns] = useState([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState('');
  const [classes, setClasses] = useState([]);
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [loadingClasses, setLoadingClasses] = useState(false);
  const [workspaceError, setWorkspaceError] = useState('');

  const refreshDesigns = useCallback(async () => {
    if (status !== 'authenticated' || user?.role !== 'Dosen') {
      setLoadingWorkspace(false);
      return [];
    }
    setLoadingWorkspace(true);
    setWorkspaceError('');
    try {
      const designs = await listRancangan({ limit: 100 });
      setAllDesigns(designs);

      setSelectedPeriodId((prev) => {
        if (prev && designs.some((d) => d.periode_id === prev)) {
          return prev;
        }
        const openDesign = designs.find((d) => !d.periode_ditutup);
        return openDesign?.periode_id || designs[0]?.periode_id || '';
      });
      return designs;
    } catch (err) {
      setWorkspaceError(err.message || 'Gagal memuat daftar penugasan Dosen.');
      return [];
    } finally {
      setLoadingWorkspace(false);
    }
  }, [status, user?.role]);

  useEffect(() => {
    refreshDesigns();
  }, [refreshDesigns]);

  const periods = useMemo(() => {
    const map = new Map();
    for (const design of allDesigns) {
      if (!map.has(design.periode_id)) {
        map.set(design.periode_id, {
          id: design.periode_id,
          tahun_akademik: design.tahun_akademik,
          semester: design.semester,
          status: design.periode_ditutup ? 'Ditutup' : 'Dibuka',
        });
      }
    }
    return [...map.values()].sort((a, b) => {
      if (a.tahun_akademik !== b.tahun_akademik) {
        return b.tahun_akademik.localeCompare(a.tahun_akademik);
      }
      if (a.semester === b.semester) return 0;
      return a.semester === 'Genap' ? -1 : 1;
    });
  }, [allDesigns]);

  const refreshClasses = useCallback(async () => {
    if (
      status !== 'authenticated' ||
      user?.role !== 'Dosen' ||
      !selectedPeriodId
    ) {
      setClasses([]);
      return [];
    }
    setLoadingClasses(true);
    try {
      const data = await listKelasMk(selectedPeriodId, { limit: 100 });
      setClasses(data);
      return data;
    } catch (err) {
      setWorkspaceError(err.message || 'Gagal memuat kelas yang diampu.');
      return [];
    } finally {
      setLoadingClasses(false);
    }
  }, [selectedPeriodId, status, user?.role]);

  useEffect(() => {
    refreshClasses();
  }, [refreshClasses]);

  const selectedPeriod = useMemo(
    () => periods.find((p) => p.id === selectedPeriodId) || null,
    [periods, selectedPeriodId],
  );

  const periodDesigns = useMemo(
    () => allDesigns.filter((d) => d.periode_id === selectedPeriodId),
    [allDesigns, selectedPeriodId],
  );

  const refreshDosenWorkspace = useCallback(async () => {
    await refreshDesigns();
    await refreshClasses();
  }, [refreshClasses, refreshDesigns]);

  return (
    <DosenWorkspaceContext.Provider
      value={{
        allDesigns,
        periodDesigns,
        periods,
        selectedPeriodId,
        setSelectedPeriodId,
        selectedPeriod,
        classes,
        loadingWorkspace: loadingWorkspace || loadingClasses,
        workspaceError,
        refreshDosenWorkspace,
      }}
    >
      {children}
    </DosenWorkspaceContext.Provider>
  );
}

export function useDosenWorkspace() {
  const ctx = useContext(DosenWorkspaceContext);
  if (!ctx) {
    throw new Error(
      'useDosenWorkspace harus digunakan di dalam DosenWorkspaceProvider',
    );
  }
  return ctx;
}
