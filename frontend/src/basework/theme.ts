import { useEffect, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
const key = 'basework.theme.v1';
export function readTheme(): ThemePreference {
  try {
    const value = localStorage.getItem(key);
    if (value === 'light' || value === 'dark') return value;
  } catch { /* Настройка работает и при недоступном хранилище браузера. */ }
  return 'system';
}
export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(readTheme);
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      const theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference;
      document.documentElement.dataset.theme = theme;
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#171d19' : '#f2f3f0');
    };
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, [preference]);
  useEffect(() => {
    const update = (event: StorageEvent) => { if (event.key === key || event.key === null) setPreference(readTheme()); };
    window.addEventListener('storage', update);
    return () => window.removeEventListener('storage', update);
  }, []);
  function choose(value: ThemePreference) {
    setPreference(value);
    try { localStorage.setItem(key, value); } catch { /* Сохраняем выбор до закрытия вкладки. */ }
  }
  return { preference, choose };
}
