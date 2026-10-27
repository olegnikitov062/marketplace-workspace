import type { Resource } from './model';

export const accessRefreshMs = 30_000;
export const accessTimeoutMs = 8_000;

export function createAccessLoader(
  request: (signal: AbortSignal) => Promise<Resource>,
  publish: (resource: Resource) => void,
  schedule: typeof setTimeout = setTimeout,
  cancel: typeof clearTimeout = clearTimeout,
) {
  let generation = 0;
  let controller: AbortController | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;
  const invalidate = () => {
    generation += 1;
    controller?.abort();
    if (timeout !== undefined) cancel(timeout);
  };
  return {
    refresh(keepVisible = false) {
      if (stopped) return;
      invalidate();
      const current = generation;
      controller = new AbortController();
      if (!keepVisible) publish({ status: 'loading' });
      timeout = schedule(() => {
        if (current !== generation) return;
        invalidate();
        publish({ status: 'unavailable' });
      }, accessTimeoutMs);
      request(controller.signal).then(result => {
        if (current === generation) publish(result);
      }).catch(() => {
        if (current === generation) publish({ status: 'unavailable' });
      }).finally(() => {
        if (current === generation && timeout !== undefined) cancel(timeout);
      });
    },
    clear() { invalidate(); publish({ status: 'loading' }); },
    stop() { stopped = true; invalidate(); },
  };
}

export async function requestLogout(allSessions: boolean, fetcher: typeof fetch = fetch): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), accessTimeoutMs);
  const options = { credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal } as const;
  try {
    const csrf = await fetcher('/auth/csrf', { ...options, headers: { Accept: 'application/json' } });
    if (!csrf.ok) throw new Error('csrf');
    const data: unknown = await csrf.json();
    if (typeof data !== 'object' || data === null || !('csrfToken' in data) ||
        typeof data.csrfToken !== 'string' || !/^[a-zA-Z0-9]{64}$/.test(data.csrfToken)) throw new Error('csrf');
    const response = await fetcher(`/api/v1/basework/${allSessions ? 'logout-all' : 'logout'}`, {
      ...options, method: 'POST', headers: { Accept: 'application/json', 'X-CSRFToken': data.csrfToken },
    });
    if (!response.ok || (await response.json()).status !== 'ok') throw new Error('logout');
  } finally { clearTimeout(timeout); }
}
