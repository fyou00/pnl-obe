import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { getMe, loginToken, logoutSession } from '../lib/adminApi.js';
import {
  clearToken,
  getToken,
  setToken,
  setUnauthorizedHandler,
} from '../lib/apiClient.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(() =>
    getToken() ? 'loading' : 'unauthenticated',
  );

  const handleUnauthorized = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(handleUnauthorized);
    return () => setUnauthorizedHandler(null);
  }, [handleUnauthorized]);

  const refreshUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setStatus('unauthenticated');
      return null;
    }
    setStatus('loading');
    try {
      const profile = await getMe();
      setUser(profile);
      setStatus('authenticated');
      return profile;
    } catch {
      clearToken();
      setUser(null);
      setStatus('unauthenticated');
      return null;
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email, password) => {
    const tokenPayload = await loginToken(email, password);
    setToken(tokenPayload.access_token);
    try {
      const profile = await getMe();
      setUser(profile);
      setStatus('authenticated');
      return profile;
    } catch (err) {
      clearToken();
      setUser(null);
      setStatus('unauthenticated');
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getToken()) {
        await logoutSession();
      }
    } catch {
      // Tetap bersihkan sesi lokal jika token sudah dicabut/kedaluwarsa.
    } finally {
      clearToken();
      setUser(null);
      setStatus('unauthenticated');
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth harus digunakan di dalam AuthProvider');
  }
  return ctx;
}
