export type Booking = { id: string; roomId: string; title: string; start: string; end: string; createdBy: string; updatedBy: string; mine: boolean; canEdit: boolean; revision: string; seriesId?: string; updatedAt?: string };
export type CalendarData = { events: Booking[]; rooms: { id: string; name: string; color?: string }[]; user: { name: string; role: 'admin' | 'employee' }; canWrite: boolean };
export function defaultBookingSlot(date: string, rooms: CalendarData['rooms'], hidden: Set<string>, lastRoom: string | null, now = new Date()) {
  const visible = rooms.filter(room => !hidden.has(room.id));
  const roomId = visible.find(room => room.id === lastRoom)?.id ?? visible[0]?.id ?? rooms[0]?.id;
  const hour = date === moscowDate(now) ? Math.max(8, Math.min(18, Number(moscowTime(now.toISOString()).slice(0, 2)) + 1)) : 10;
  return { date, roomId, start: minuteTime(hour * 60), end: minuteTime((hour + 1) * 60) };
}
// Сохраняем оттенок комнаты из источника, снижая насыщенность под тему BaseWork.
export const roomColor = (room: CalendarData['rooms'][number], index: number) =>
  `color-mix(in srgb, ${room.color ?? ['#567868', '#63778a'][index % 2]} 25%, var(--bw-muted))`;
export type CalendarResult = { status: 'ready'; data: CalendarData } | { status: 'expired' | 'forbidden' | 'unbound' | 'unavailable' | 'error' | 'loading' };
export type Mutation = { method: 'POST' | 'PUT' | 'DELETE'; id?: string; body: Record<string, unknown>; operation: string };
export type BookingConflict = Pick<Booking, 'roomId' | 'title' | 'start' | 'end'>;
export type MutationResult = { status: 'ok'; skipped: number } | { status: 'conflict'; conflicts?: BookingConflict[] } | { status: 'unknown' | 'stale' | 'expired' | 'forbidden' | 'invalid' | 'not_found' };
// Только память вкладки: смена видимости не должна терять ключ незавершённой записи.
const pending = new Map<string, Mutation>();
export const pendingBooking = (actor: string) => pending.get(actor);
export const rememberBooking = (actor: string, mutation: Mutation) => { pending.set(actor, mutation); };
export const settleBooking = (actor: string, operation: string) => { if (pending.get(actor)?.operation === operation) pending.delete(actor); };
const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

export function parseCalendar(value: unknown): CalendarResult {
  if (!object(value) || !Array.isArray(value.events) || !Array.isArray(value.rooms) || typeof value.canWrite !== 'boolean' ||
      !object(value.user) || typeof value.user.name !== 'string' || !['admin', 'employee'].includes(String(value.user.role))) return { status: 'error' };
  if (!value.rooms.every(r => object(r) && typeof r.id === 'string' && typeof r.name === 'string' &&
      (r.color === undefined || (typeof r.color === 'string' && /^#[a-fA-F0-9]{6}$/.test(r.color))))) return { status: 'error' };
  const rooms = value.rooms as CalendarData['rooms'];
  if (!value.events.every(ev => object(ev) && ['id', 'roomId', 'title', 'start', 'end', 'createdBy', 'updatedBy', 'revision'].every(k => typeof ev[k] === 'string') &&
      typeof ev.mine === 'boolean' && typeof ev.canEdit === 'boolean' && rooms.some(r => r.id === ev.roomId) &&
      /^[a-f0-9]{32}$/.test(String(ev.id)) && /^[a-f0-9]{64}$/.test(String(ev.revision)) &&
      Number.isFinite(Date.parse(String(ev.start))) && Date.parse(String(ev.end)) > Date.parse(String(ev.start)) &&
      (ev.seriesId === undefined || typeof ev.seriesId === 'string') &&
      (ev.updatedAt === undefined || (typeof ev.updatedAt === 'string' && Number.isFinite(Date.parse(ev.updatedAt)))))) return { status: 'error' };
  if (new Set(value.events.map(ev => ev.id)).size !== value.events.length || new Set(rooms.map(r => r.id)).size !== rooms.length) return { status: 'error' };
  return { status: 'ready', data: { events: value.events as Booking[], rooms, user: value.user as CalendarData['user'], canWrite: value.canWrite } };
}

export const moscowDate = (instant = new Date()) => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit' }).format(instant);
export const shiftDate = (date: string, days: number) => new Date(Date.parse(date + 'T12:00:00Z') + days * 86400000).toISOString().slice(0, 10);
export const weekDay = (date: string) => new Date(date + 'T12:00:00Z').getUTCDay();
export const monday = (date: string) => shiftDate(date, -((weekDay(date) + 6) % 7));
export const moscowTime = (instant: string) => new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(instant));
export type CalendarView = 'day' | 'week' | 'month';
export const shiftMonth = (date: string, count: number) => new Date(Date.UTC(Number(date.slice(0, 4)), Number(date.slice(5, 7)) - 1 + count, 1, 12)).toISOString().slice(0, 10);
export const defaultRepeatUntil = (date: string) => {
  const until = new Date(date + 'T12:00:00Z');
  until.setUTCMonth(until.getUTCMonth() + 3);
  return until.toISOString().slice(0, 10);
};
export function conflictMessage(conflicts: BookingConflict[] = [], rooms: CalendarData['rooms'] = []) {
  if (!conflicts.length) return 'Переговорка занята. Измените время или явно пропустите занятые повторы.';
  return 'Занятые интервалы: ' + conflicts.map(item => `${rooms.find(room => room.id === item.roomId)?.name ?? 'Переговорка'}, ${moscowDate(new Date(item.start))}, ${moscowTime(item.start)}–${moscowTime(item.end)} — «${item.title}»`).join('; ') + '. Показано до трёх конфликтов. Измените время или пропустите занятые повторы.';
}
export function calendarRange(date: string, view: CalendarView) {
  const from = view === 'month' ? monday(date.slice(0, 8) + '01') : view === 'week' ? monday(date) : date;
  return { from, to: shiftDate(from, view === 'month' ? 42 : view === 'week' ? 7 : 1) };
}
export const minuteTime = (minute: number) => `${String(Math.floor(minute / 60)).padStart(2, '0')}:${String(minute % 60).padStart(2, '0')}`;
export const atMinute = (date: string, minute: number) => new Date(Date.parse(date + 'T00:00:00+03:00') + minute * 60000).toISOString();
export type RepeatRule = { unit: 'day' | 'week' | 'month'; interval: number; days: number[]; count?: number; until?: string };
export function repeatOccurrences(date: string, start: string, end: string, rule: RepeatRule | null) {
  const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value + 'T12:00:00Z')) && new Date(value + 'T12:00:00Z').toISOString().slice(0, 10) === value;
  if (!validDate(date) || !/^(0\d|1\d|2[0-3]):[0-5]\d$/.test(start) || !/^(0\d|1\d|2[0-3]):[0-5]\d$/.test(end) || start < '08:00' || end > '19:00' || end <= start) throw new Error('Проверьте дату и время: Москва, 08:00–19:00.');
  if (rule && (!Number.isInteger(rule.interval) || rule.interval < 1 || rule.interval > 99 ||
      (rule.count !== undefined && (!Number.isInteger(rule.count) || rule.count < 1 || rule.count > 200)) ||
      (rule.until !== undefined && (!validDate(rule.until) || rule.until < date)) ||
      (rule.count === undefined && rule.until === undefined) ||
      (rule.unit === 'week' && (!rule.days.length || rule.days.some(d => !Number.isInteger(d) || d < 0 || d > 6))))) throw new Error('Проверьте правило повторения и дату окончания.');
  const dates: string[] = [];
  const limit = rule?.count ?? (rule ? 201 : 1);
  const add = (day: string) => {
    if (day < date) return false;
    if ((rule?.until && day > rule.until) || dates.length >= limit) return true;
    if ([0, 6].includes(weekDay(day))) throw new Error(`Повтор ${day} приходится на выходной. Выберите будние дни или другое правило.`);
    dates.push(day); return dates.length >= limit;
  };
  if (!rule) add(date);
  else if (rule.unit === 'month') {
    for (let i = 0; i < 1200; i++) {
      const month = shiftMonth(date, i * rule.interval);
      const day = month.slice(0, 8) + date.slice(8);
      if (rule.until && day > rule.until) break;
      if (!validDate(day)) continue;
      if (add(day)) break;
    }
  } else if (rule.unit === 'week') {
    const days = [1, 2, 3, 4, 5, 6, 0].filter(d => rule.days.includes(d));
    outer: for (let i = 0; i < 5000; i += rule.interval) {
      for (const day of days) if (add(shiftDate(monday(date), i * 7 + (day + 6) % 7))) break outer;
    }
  } else {
    for (let i = 0; i < 5000; i++) if (add(shiftDate(date, i * rule.interval))) break;
  }
  if (!dates.length || dates.length > 200 || (rule?.count !== undefined && dates.length !== rule.count)) throw new Error('В серии должно быть от 1 до 200 встреч. Уменьшите период повторения.');
  return dates.map(day => ({ start: `${day}T${start}:00+03:00`, end: `${day}T${end}:00+03:00` }));
}

export function layoutBookings(events: Booking[], day: string, room?: string) {
  const midnight = Date.parse(day + 'T00:00:00+03:00');
  const items = events.filter(ev => (!room || ev.roomId === room) && Date.parse(ev.end) > midnight && Date.parse(ev.start) < midnight + 86400000)
    .map(ev => ({ ev, start: Math.max(0, (Date.parse(ev.start) - midnight) / 60000), end: Math.min(1440, (Date.parse(ev.end) - midnight) / 60000), column: 0, columns: 1 }))
    .sort((a, b) => a.start - b.start || b.end - a.end);
  let group: typeof items = [], ends: number[] = [], groupEnd = -1;
  const flush = () => { group.forEach(item => { item.columns = ends.length; }); group = []; ends = []; };
  for (const item of items) {
    if (item.start >= groupEnd) { flush(); groupEnd = -1; }
    let column = ends.findIndex(end => end <= item.start);
    if (column < 0) { column = ends.length; ends.push(item.end); } else ends[column] = item.end;
    item.column = column; group.push(item); groupEnd = Math.max(groupEnd, item.end);
  }
  flush(); return items;
}
export function occurrences(date: string, start: string, end: string, repeat: string, count: number) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(start) || !/^\d{2}:\d{2}$/.test(end) ||
      start < '08:00' || end > '19:00' || end <= start || !Number.isInteger(count) || count < 1 || count > 200 ||
      !['none', 'workdays', 'weekly', 'biweekly'].includes(repeat)) throw new Error('Проверьте дату, время и число повторов.');
  let cursor = date;
  return Array.from({ length: repeat === 'none' ? 1 : count }, (_, index) => {
    if (index) {
      cursor = shiftDate(cursor, repeat === 'weekly' ? 7 : repeat === 'biweekly' ? 14 : 1);
      if (repeat === 'workdays') while ([0, 6].includes(weekDay(cursor))) cursor = shiftDate(cursor, 1);
    }
    if ([0, 6].includes(weekDay(cursor)) || !Number.isFinite(Date.parse(cursor))) throw new Error('Выберите будний день.');
    return { start: cursor + 'T' + start + ':00+03:00', end: cursor + 'T' + end + ':00+03:00' };
  });
}

export async function readCalendar(from: string, to: string, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<CalendarResult> {
  if ((Date.parse(to) - Date.parse(from)) / 86400000 > 35) {
    // Месячная сетка содержит 42 дня; серверный лимит не расширяем.
    const middle = shiftDate(from, 21);
    const results = await Promise.all([readCalendar(from, middle, signal, fetcher), readCalendar(middle, to, signal, fetcher)]);
    const [left, right] = results;
    if (left.status !== 'ready') return left;
    if (right.status !== 'ready') return right;
    if (JSON.stringify(left.data.rooms) !== JSON.stringify(right.data.rooms) || JSON.stringify(left.data.user) !== JSON.stringify(right.data.user) || left.data.canWrite !== right.data.canWrite) return { status: 'error' };
    const events = new Map(left.data.events.map(ev => [ev.id, ev]));
    for (const ev of right.data.events) {
      if (events.has(ev.id) && events.get(ev.id)?.revision !== ev.revision) return { status: 'error' };
      events.set(ev.id, ev);
    }
    return { status: 'ready', data: { ...left.data, events: [...events.values()] } };
  }
  const response = await fetcher('/api/v1/basework/rooms/events?' + new URLSearchParams({ from: from + 'T00:00:00+03:00', to: to + 'T00:00:00+03:00' }),
    { credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal, headers: { Accept: 'application/json' } });
  if (response.status === 401) return { status: 'expired' };
  if (response.status === 403) {
    const value = await response.json().catch(() => ({}));
    return { status: value.status === 'identity_unbound' ? 'unbound' : 'forbidden' };
  }
  if ([404, 502, 503, 504].includes(response.status)) return { status: 'unavailable' };
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return { status: 'error' };
  return parseCalendar(await response.json().catch(() => null));
}

export async function writeBooking(mutation: Mutation, csrf: string, signal: AbortSignal, fetcher: typeof fetch = fetch): Promise<MutationResult> {
  try {
    const response = await fetcher('/api/v1/basework/rooms/events' + (mutation.id ? '/' + encodeURIComponent(mutation.id) : ''), {
      method: mutation.method, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'Idempotency-Key': mutation.operation }, body: JSON.stringify(mutation.body),
    });
    if (response.status === 401) return { status: 'expired' };
    if (response.status === 403) return { status: 'forbidden' };
    if (response.status === 404) return { status: 'not_found' };
    if (response.status === 400) return { status: 'invalid' };
    const value = await response.json().catch(() => null);
    if (response.status === 409) {
      if (object(value) && ['stale', 'operation_conflict'].includes(String(value.status))) return { status: 'stale' };
      const conflicts = object(value) && Array.isArray(value.conflicts) ? value.conflicts.slice(0, 3).filter((item): item is BookingConflict => object(item) &&
        ['roomId', 'title', 'start', 'end'].every(key => typeof item[key] === 'string') &&
        Number.isFinite(Date.parse(String(item.start))) && Date.parse(String(item.end)) > Date.parse(String(item.start))) : [];
      return { status: 'conflict', conflicts };
    }
    if (response.ok && object(value) && (Array.isArray(value.created) || typeof value.updated === 'number' || typeof value.deleted === 'number')) {
      return { status: 'ok', skipped: typeof value.skipped === 'number' ? value.skipped : 0 };
    }
    return { status: 'unknown' };
  } catch { return { status: 'unknown' }; }
}
