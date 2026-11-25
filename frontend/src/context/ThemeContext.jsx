import { createContext, useContext, useEffect } from 'react';

const THEME_STORAGE_KEY = 'pnl_obe_theme';

const ThemeContext = createContext(null);

const noop = () => {};

export function ThemeProvider({ children }) {
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', 'light');
    root.classList.remove('dark');
    try {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } catch {
      // Abaikan jika penyimpanan browser dibatasi.
    }
  }, []);

  return (
    <ThemeContext.Provider
      value={{
        theme: 'light',
        isDark: false,
        setTheme: noop,
        toggleTheme: noop,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme harus digunakan di dalam ThemeProvider');
  }
  return ctx;
}
