import { useEffect, useState } from 'react';
import { requestAuthOptions, type AuthOptions } from './authOptions';
import { accessTimeoutMs } from './session';

export function useAuthOptions() {
  const [options, setOptions] = useState<AuthOptions>('unavailable');
  useEffect(() => {
    let active = true;
    let controller: AbortController | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => {
      controller?.abort();
      clearTimeout(timer);
      const current = new AbortController();
      controller = current;
      setOptions('unavailable');
      timer = setTimeout(() => current.abort(), accessTimeoutMs);
      requestAuthOptions(current.signal).then(value => {
        if (active && controller === current && !current.signal.aborted) setOptions(value);
      }).catch(() => {
        if (active && controller === current) setOptions('unavailable');
      }).finally(() => { if (controller === current) clearTimeout(timer); });
    };
    const visible = () => { if (document.visibilityState === 'visible') refresh(); };
    refresh();
    window.addEventListener('pageshow', refresh);
    document.addEventListener('visibilitychange', visible);
    return () => {
      active = false;
      controller?.abort();
      clearTimeout(timer);
      window.removeEventListener('pageshow', refresh);
      document.removeEventListener('visibilitychange', visible);
    };
  }, []);
  return options;
}
