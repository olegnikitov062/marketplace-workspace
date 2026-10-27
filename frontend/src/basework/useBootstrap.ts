import { useCallback, useEffect, useRef, useState } from 'react';
import { requestBootstrap, type Resource } from './model';
import { accessRefreshMs, createAccessLoader, requestLogout } from './session';

export function useBootstrap() {
  const [resource, setResource] = useState<Resource>({ status: 'loading' });
  const loader = useRef<ReturnType<typeof createAccessLoader> | null>(null);
  const pendingLogout = useRef(false);
  const retry = useCallback(() => { if (!pendingLogout.current) loader.current?.refresh(); }, []);
  const logout = useCallback(async (allSessions: boolean) => {
    if (pendingLogout.current) return;
    pendingLogout.current = true;
    loader.current?.clear();
    try {
      await requestLogout(allSessions);
    } finally {
      pendingLogout.current = false;
      loader.current?.refresh();
    }
  }, []);
  useEffect(() => {
    const current = createAccessLoader(requestBootstrap, setResource);
    loader.current = current;
    current.refresh();
    const timer = window.setInterval(() => {
      if (!pendingLogout.current && document.visibilityState === 'visible') current.refresh(true);
    }, accessRefreshMs);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') retry();
      else current.clear();
    };
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pageshow', retry);
    return () => {
      current.stop();
      loader.current = null;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pageshow', retry);
    };
  }, [retry]);
  return { resource, retry, logout };
}
