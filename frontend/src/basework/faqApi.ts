export type Person = { name: string; role: string };
export type Question = { id: string; cat: string; q: string; contacts: [string, string][] };
export type FaqDocument = {
  version: number; updatedAt: string; people: Person[]; items: Question[]; categories: string[]; total: number;
};
export type FaqResource =
  | { status: 'loading' | 'error' | 'unavailable' | 'forbidden' | 'expired' | 'mfa_required' }
  | { status: 'ready'; data: FaqDocument };

const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
export function parseFaq(value: unknown): FaqResource {
  if (!object(value) || !Number.isSafeInteger(value.version) || (value.version as number) < 0 ||
      typeof value.updatedAt !== 'string' || !Number.isSafeInteger(value.total) || (value.total as number) < 0 ||
      !Array.isArray(value.people) || !Array.isArray(value.items) || !Array.isArray(value.categories) ||
      !value.categories.every(cat => typeof cat === 'string' && cat.length > 0)) return { status: 'error' };
  if (!value.people.every(person => object(person) && typeof person.name === 'string' && person.name && typeof person.role === 'string')) return { status: 'error' };
  const people = value.people as Person[];
  const names = new Set(people.map(person => person.name));
  if (names.size !== people.length || !value.items.every(item => object(item) &&
      typeof item.id === 'string' && item.id && typeof item.cat === 'string' && value.categories instanceof Array && value.categories.includes(item.cat) &&
      typeof item.q === 'string' && item.q && Array.isArray(item.contacts) && item.contacts.every(contact =>
        Array.isArray(contact) && contact.length === 2 && typeof contact[0] === 'string' && names.has(contact[0]) && typeof contact[1] === 'string'))) return { status: 'error' };
  const items = value.items as Question[];
  if (new Set(items.map(item => item.id)).size !== items.length || items.length > (value.total as number)) return { status: 'error' };
  return { status: 'ready', data: { version: value.version as number, updatedAt: value.updatedAt,
    people, items, categories: value.categories as string[], total: value.total as number } };
}

export async function requestFaq(query: string, category: string, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<FaqResource> {
  const params = new URLSearchParams({ q: query, category });
  const response = await fetcher(`/api/v1/basework/faq/items?${params}`, {
    credentials: 'same-origin', cache: 'no-store', redirect: 'error', headers: { Accept: 'application/json' }, signal,
  });
  if (response.status === 401) return { status: 'expired' };
  if (response.status === 403) {
    try { return { status: (await response.json()).status === 'mfa_required' ? 'mfa_required' : 'forbidden' }; }
    catch { return { status: 'forbidden' }; }
  }
  if ([404, 502, 503, 504].includes(response.status)) return { status: 'unavailable' };
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return { status: 'error' };
  try { return parseFaq(await response.json()); }
  catch { return { status: 'error' }; }
}
