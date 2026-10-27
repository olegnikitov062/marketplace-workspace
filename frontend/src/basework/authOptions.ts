export type AuthOptions = 'enabled' | 'disabled' | 'unavailable';
export const oidcLoginPath = '/auth/basework/oidc/login';

export async function requestAuthOptions(signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<AuthOptions> {
  const response = await fetcher('/api/v1/basework/auth-options', {
    signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return 'unavailable';
  try {
    const value: unknown = await response.json();
    if (typeof value !== 'object' || value === null || !('oidcEnabled' in value) ||
        typeof value.oidcEnabled !== 'boolean') return 'unavailable';
    return value.oidcEnabled ? 'enabled' : 'disabled';
  } catch { return 'unavailable'; }
}
