import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { Dialog } from './Dialog';
import { RoomsGrid, type Slot } from './RoomsGrid';
import './rooms.css';
import { readCalendar, writeBooking, moscowDate, moscowTime, shiftDate, weekDay, minuteTime, repeatOccurrences, calendarRange, shiftMonth,
  pendingBooking, rememberBooking, settleBooking, roomColor, defaultBookingSlot, defaultRepeatUntil, conflictMessage,
  type Booking, type CalendarData, type CalendarResult, type Mutation, type CalendarView, type RepeatRule } from './roomsApi';

const messages = {
  loading: ['Загружаем календарь…', 'Проверяем доступ и получаем брони.'],
  expired: ['Сессия завершена', 'Войдите снова, чтобы открыть календарь.'],
  forbidden: ['Нет доступа', 'Разрешение отозвано или профиль переговорок недоступен.'],
  unbound: ['Профиль переговорок не связан', 'Администратору нужно связать ваш аккаунт с существующим профилем переговорок.'],
  unavailable: ['Переговорки недоступны', 'Источник не подключён или не отвечает. Повторите проверку позже.'],
  error: ['Не удалось загрузить календарь', 'Проверьте соединение и повторите запрос.'],
};
const dateLabel = (date: string) => new Intl.DateTimeFormat('ru-RU', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(date + 'T12:00:00Z'));

function BookingForm({ actor, data, initial, day, selected, csrf, suspended, close, saved, denied }: {
  actor: string; data: CalendarData; initial: Booking | null; day: string; selected?: Slot; csrf: string;
  suspended: boolean;
  close: () => void; saved: (message: string) => void; denied: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? '');
  const [room, setRoom] = useState(initial?.roomId ?? selected?.roomId ?? data.rooms[0]?.id ?? '');
  const [date, setDate] = useState(initial ? moscowDate(new Date(initial.start)) : selected?.date ?? day);
  const [start, setStart] = useState(initial ? moscowTime(initial.start) : selected?.start ?? '09:00');
  const [end, setEnd] = useState(initial ? moscowTime(initial.end) : selected?.end ?? '10:00');
  const [repeat, setRepeat] = useState('none');
  const [count, setCount] = useState(10);
  const [endType, setEndType] = useState<'until' | 'count'>('until');
  const [until, setUntil] = useState(defaultRepeatUntil(selected?.date ?? day));
  const [unit, setUnit] = useState<RepeatRule['unit']>('week');
  const [interval, setInterval] = useState(1);
  const [days, setDays] = useState([weekDay(selected?.date ?? day)]);
  const [scope, setScope] = useState('one');
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const [unknown, setUnknown] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const operation = useRef<Mutation | null>(null);
  const active = useRef(true);
  const sending = useRef(false);
  const readonly = !data.canWrite || (initial !== null && !data.events.some(event => event.id === initial.id && event.canEdit));
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const rule = (): RepeatRule | null => {
    if (initial || repeat === 'none') return null;
    const ending = endType === 'count' ? { count } : { until };
    if (repeat === 'custom') return { unit, interval, days, ...ending };
    return { unit: repeat === 'monthly' ? 'month' : repeat === 'daily' ? 'day' : 'week',
      interval: repeat === 'biweekly' ? 2 : 1, days: repeat === 'workdays' ? [1, 2, 3, 4, 5] : [weekDay(date)], ...ending };
  };
  let summary = '';
  if (!initial && repeat !== 'none') {
    try { summary = `Встреч: ${repeatOccurrences(date, start, end, rule()).length}.`; }
    catch (error) { summary = error instanceof Error ? error.message : ''; }
  }
  const execute = async (mutation: Mutation) => {
    if (sending.current || suspended || !data.canWrite || document.visibilityState !== 'visible') return;
    // Удалённая или перенесённая бронь может исчезнуть из текущего диапазона.
    // Восстанавливаем только сохранённую операцию этого аккаунта; новый запрос
    // по-прежнему требует canEdit. Источник заново проверяет права и квитанцию.
    if (unknown ? mutation !== operation.current || mutation !== pendingBooking(actor) : readonly) return;
    sending.current = true; operation.current = mutation;
    rememberBooking(actor, mutation);
    setPending(true); setMessage(''); setConflict(false);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    const result = await writeBooking(mutation, csrf, controller.signal);
    window.clearTimeout(timeout); sending.current = false;
    if (result.status !== 'unknown') settleBooking(actor, mutation.operation);
    if (!active.current) return;
    setPending(false);
    if (result.status === 'ok') { saved(result.skipped ? `Сохранено. Пропущено занятых интервалов: ${result.skipped}.` : mutation.method === 'DELETE' ? 'Бронь отменена.' : 'Бронь сохранена.'); return; }
    if (result.status === 'expired' || result.status === 'forbidden') { denied(); return; }
    setUnknown(result.status === 'unknown'); setConflict(result.status === 'conflict');
    setMessage({ unknown: 'Ответ не получен. Не создавайте новую бронь и не обновляйте страницу. Проверьте результат тем же запросом.',
      conflict: result.status === 'conflict' ? conflictMessage(result.conflicts, data.rooms) : '',
      stale: 'Бронь или серия изменилась. Черновик сохранён; закройте форму и откройте актуальную бронь перед повторным редактированием.',
      invalid: 'Проверьте поля: Москва, будни 08:00–19:00. Не более 200 повторов.',
      not_found: 'Бронь уже удалена. Черновик сохранён.' }[result.status]);
  };
  const submit = (skipConflicts = false) => {
    if (suspended || readonly || pending || unknown || document.visibilityState !== 'visible') return;
    try {
      const times = repeatOccurrences(date, start, end, rule());
      if (!title.trim() || title.trim().length > 200) throw new Error('Введите описание до 200 символов.');
      const body = initial ? { roomId: room, title: title.trim(), ...times[0], scope, expectedRevision: initial.revision } :
        { roomId: room, title: title.trim(), occurrences: times, skipConflicts };
      try { localStorage.setItem('bw.rooms.lastRoom', room); } catch { /* Настройка необязательна. */ }
      void execute({ method: initial ? 'PUT' : 'POST', id: initial?.id, body, operation: crypto.randomUUID() });
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Проверьте поля.'); }
  };
  // Состояние остаётся только в памяти компонента, DOM и действия недоступны
  // до новой проверки оболочки и календаря. Исходную revision не обновляем.
  if (suspended) return null;
  return <Dialog title={initial ? 'Бронь переговорки' : 'Новая бронь'} onClose={() => { if (!pending && !unknown) close(); }}>
    <p className="bw-muted">Москва · Пн–Пт, 08:00–19:00</p>
    {initial ? <p>Автор: {initial.createdBy}. Последнее изменение: {initial.updatedBy}{initial.updatedAt ? `, ${dateLabel(moscowDate(new Date(initial.updatedAt)))}, ${moscowTime(initial.updatedAt)}` : ''}.</p> : null}
    {readonly && !unknown ? <p>Эта бронь доступна только для просмотра.</p> : null}
    <form onSubmit={event => { event.preventDefault(); submit(); }}>
      <fieldset className="bw-room-form" disabled={pending || unknown || readonly}>
        <label>Переговорка<select value={room} onChange={e => setRoom(e.target.value)}>{data.rooms.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
        <label>Описание<input data-dialog-focus required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} /></label>
        <label>Дата<input type="date" required value={date} onChange={e => { const next = e.target.value; setDate(next); if (next && days.length === 1) setDays([weekDay(next)]); }} /></label>
        {!readonly && date && [0, 6].includes(weekDay(date)) ? <p role="status">Выбран выходной. Для сохранения брони выберите будний день — с понедельника по пятницу.</p> : null}
        <div className="bw-room-times"><label>Начало<input type="time" required min="08:00" max="18:59" value={start} onChange={e => setStart(e.target.value)} /></label>
          <label>Окончание<input type="time" required min="08:01" max="19:00" value={end} onChange={e => setEnd(e.target.value)} /></label></div>
        {!readonly ? <div className="bw-quick-duration">{[30, 60, 90, 120].map((minutes, index) => <button className="bw-button" type="button" key={minutes}
          onClick={() => { const [h, m] = start.split(':').map(Number); setEnd(minuteTime(Math.min(1140, h * 60 + m + minutes))); }}>{['30 мин', '1 ч', '1,5 ч', '2 ч'][index]}</button>)}</div> : null}
        {!initial ? <><label>Повтор<select value={repeat} onChange={e => setRepeat(e.target.value)}><option value="none">Не повторять</option><option value="daily">Каждый день</option><option value="workdays">По будням (пн–пт)</option><option value="weekly">Каждую неделю</option><option value="biweekly">Каждые 2 недели</option><option value="monthly">Каждый месяц</option><option value="custom">Настроить…</option></select></label>
          {repeat !== 'none' ? <div className="bw-repeat-settings">
            {repeat === 'custom' ? <><div className="bw-room-times"><label>Повторять раз в<input type="number" min="1" max="99" value={interval} onChange={e => setInterval(Number(e.target.value))} /></label>
              <label>Единица<select value={unit} onChange={e => setUnit(e.target.value as RepeatRule['unit'])}><option value="day">день</option><option value="week">неделю</option><option value="month">месяц</option></select></label></div>
              {unit === 'week' ? <div className="bw-repeat-days" aria-label="Дни повторения">{[1, 2, 3, 4, 5, 6, 0].map((d, i) => <button type="button" className="bw-button" key={d} aria-pressed={days.includes(d)} disabled={[0, 6].includes(d)} onClick={() => setDays(previous => previous.includes(d) ? previous.filter(day => day !== d) : [...previous, d])}>{['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i]}</button>)}</div> : null}</> : null}
            <label className="bw-repeat-end"><input type="radio" name="repeat-end" checked={endType === 'until'} onChange={() => setEndType('until')} />До даты<input type="date" aria-label="Повторять до" value={until} onChange={e => setUntil(e.target.value)} disabled={endType !== 'until'} /></label>
            <label className="bw-repeat-end"><input type="radio" name="repeat-end" checked={endType === 'count'} onChange={() => setEndType('count')} />Всего<input aria-label="Количество повторов" type="number" min="1" max="200" value={count} onChange={e => setCount(Number(e.target.value))} disabled={endType !== 'count'} />раз</label>
            <p className="bw-muted">{summary}</p></div> : null}</> : null}
        {initial?.seriesId && !readonly ? <div className="bw-room-scope" role="group" aria-label="Применить изменение серии"><p>Повторяющаяся бронь. Применить к:</p>
          {(['one', 'following', 'all'] as const).map((value, index) => <label key={value}><input type="radio" name="booking-scope" checked={scope === value} onChange={() => setScope(value)} />{['Только этой встрече', 'Этой и следующим', 'Всей серии'][index]}</label>)}</div> : null}
        {!readonly ? <div className="bw-room-actions"><button className="bw-button" type="submit">{pending ? 'Сохраняем…' : 'Сохранить'}</button>
          <button type="button" className="bw-button" onClick={close}>Отмена</button>
          {initial ? <button type="button" className="bw-button" onClick={() => setConfirmDelete(true)}>Отменить бронь</button> : null}</div> : null}
        {confirmDelete && initial ? <div role="group" aria-label="Подтверждение отмены"><p>Отменить {scope === 'all' ? 'всю серию' : scope === 'following' ? 'эту и следующие встречи' : 'эту встречу'}?</p>
          <button className="bw-button" type="button" onClick={() => void execute({ method: 'DELETE', id: initial.id, body: { scope, expectedRevision: initial.revision }, operation: crypto.randomUUID() })}>Подтвердить отмену</button></div> : null}
      </fieldset>
    </form>
    {message ? <p role="alert">{message}</p> : null}
    {unknown && !data.canWrite ? <p role="status">Запись временно отключена. Для подтверждения результата обратитесь к администратору; не повторяйте операцию заново.</p> : null}
    {unknown ? <button className="bw-button" disabled={pending || !data.canWrite} type="button" onClick={() => { if (operation.current) void execute(operation.current); }}>Проверить результат</button> : null}
    {conflict && !initial && repeat !== 'none' ? <button className="bw-button" disabled={pending || readonly} type="button" onClick={() => submit(true)}>Сохранить свободные повторы</button> : null}
  </Dialog>;
}

export function Rooms({ csrf, actor, authorized, accessPanel }: { csrf: string; actor: string; authorized: boolean; accessPanel: ReactNode }) {
  const [date, setDate] = useState(moscowDate);
  const [view, setView] = useState<CalendarView>(() => {
    try { const saved = localStorage.getItem('bw.rooms.view'); if (saved === 'day' || saved === 'week' || saved === 'month') return saved; } catch { /* Настройка необязательна. */ }
    return window.innerWidth < 640 ? 'day' : 'week';
  });
  const [hidden, setHidden] = useState<Set<string>>(() => {
    try { const value = JSON.parse(localStorage.getItem('bw.rooms.hidden') ?? '[]'); if (Array.isArray(value) && value.every(x => typeof x === 'string')) return new Set(value); } catch { /* Настройка необязательна. */ }
    return new Set();
  });
  const [resource, setResource] = useState<CalendarResult>({ status: 'loading' });
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<{ initial: Booking | null; data: CalendarData; selected?: Slot } | null>(null);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    if (!authorized || ['expired', 'forbidden', 'unbound'].includes(resource.status)) setNotice('');
  }, [authorized, resource.status]);
  const [recovering, setRecovering] = useState(false);
  const writeActive = useRef(false);
  const lastRange = useRef('');
  const scrollPosition = useRef(360);
  const [scrollReset, setScrollReset] = useState(0);
  const today = () => { scrollPosition.current = 360; setScrollReset(value => value + 1); setDate(moscowDate()); };
  const unresolved = !editing ? pendingBooking(actor) : undefined;
  const recover = async () => {
    if (!unresolved || recovering) return;
    setRecovering(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    const result = await writeBooking(unresolved, csrf, controller.signal);
    window.clearTimeout(timeout);
    if (result.status !== 'unknown') settleBooking(actor, unresolved.operation);
    setRecovering(false);
    setNotice(result.status === 'ok' ? 'Результат предыдущей операции подтверждён. Календарь обновлён.' : result.status === 'unknown' ?
      'Ответ ещё не получен. Повторная проверка использует прежний запрос.' : 'Предыдущая операция отклонена. Сверьте актуальный календарь перед новой записью.');
    setReload(x => x + 1);
  };
  const { from, to } = calendarRange(date, view);
  const changeView = (value: CalendarView) => { setView(value); try { localStorage.setItem('bw.rooms.view', value); } catch { /* Настройка необязательна. */ } };
  const shift = (direction: number) => setDate(current => view === 'month' ? shiftMonth(current, direction) : shiftDate(current, direction * (view === 'week' ? 7 : 1)));
  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      if (editing || document.querySelector('dialog[open]') || event.metaKey || event.ctrlKey || event.altKey || (event.target as HTMLElement).matches('input, select, textarea, [contenteditable="true"]')) return;
      const key = event.key.toLowerCase();
      if (key === 'arrowleft') { event.preventDefault(); shift(-1); }
      else if (key === 'arrowright') { event.preventDefault(); shift(1); }
      else if (['t', 'е'].includes(key)) today();
      else if (['d', 'в'].includes(key)) changeView('day');
      else if (['w', 'ц'].includes(key)) changeView('week');
      else if (['m', 'ь'].includes(key)) changeView('month');
    };
    document.addEventListener('keydown', keyboard);
    return () => document.removeEventListener('keydown', keyboard);
  }, [view, editing]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (pendingBooking(actor)) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [actor]);
  useEffect(() => {
    if (!authorized) { setResource({ status: 'loading' }); return; }
    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    if (lastRange.current !== from + to) setResource({ status: 'loading' });
    lastRange.current = from + to;
    void readCalendar(from, to, controller.signal).then(result => {
      if (!active) return;
      setResource(result);
      if (['expired', 'forbidden', 'unbound'].includes(result.status)) setEditing(null);
    }).catch(() => { if (active) setResource({ status: 'error' }); }).finally(() => window.clearTimeout(timeout));
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [from, to, reload, authorized]);
  useEffect(() => {
    const timer = window.setInterval(() => { if (authorized && document.visibilityState === 'visible') setReload(x => x + 1); }, 30000);
    return () => window.clearInterval(timer);
  }, [authorized]);
  const data = authorized && resource.status === 'ready' ? resource.data : null;
  const create = (selected?: Slot) => { if (data?.canWrite && !pendingBooking(actor) && !writeActive.current) {
    let lastRoom: string | null = null;
    try { lastRoom = localStorage.getItem('bw.rooms.lastRoom'); } catch { /* Настройка необязательна. */ }
    const defaults = defaultBookingSlot(selected?.date ?? date, data.rooms, hidden, lastRoom);
    setNotice(''); setEditing({ initial: null, data, selected: { ...defaults, ...selected, roomId: selected?.roomId ?? defaults.roomId } });
  } };
  const move = async (ev: Booking, changes: { start: string; end: string; roomId: string }) => {
    if (!data?.canWrite || !ev.canEdit || pendingBooking(actor) || writeActive.current) return;
    try { repeatOccurrences(moscowDate(new Date(changes.start)), moscowTime(changes.start), moscowTime(changes.end), null); }
    catch (error) { setNotice(error instanceof Error ? error.message : 'Проверьте интервал.'); return; }
    writeActive.current = true; setRecovering(true);
    const mutation: Mutation = { method: 'PUT', id: ev.id, operation: crypto.randomUUID(), body: { ...changes, title: ev.title, scope: 'one', expectedRevision: ev.revision } };
    rememberBooking(actor, mutation);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    const result = await writeBooking(mutation, csrf, controller.signal);
    window.clearTimeout(timeout);
    if (result.status !== 'unknown') settleBooking(actor, mutation.operation);
    writeActive.current = false; setRecovering(false);
    setNotice(result.status === 'ok' ? `Перенесено: ${dateLabel(moscowDate(new Date(changes.start)))}, ${moscowTime(changes.start)}–${moscowTime(changes.end)}.` :
      result.status === 'conflict' ? `Перенос не выполнен. ${conflictMessage(result.conflicts, data.rooms)}` : result.status === 'unknown' ? 'Ответ о переносе не получен. Проверьте предыдущую операцию.' :
        result.status === 'stale' ? 'Бронь изменилась. Календарь обновлён; повторите перенос с актуальной версией.' : 'Перенос отклонён. Проверьте доступ и время.');
    setReload(x => x + 1);
  };
  const title = view === 'month' ? new Intl.DateTimeFormat('ru-RU', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(new Date(date + 'T12:00:00Z')) :
    view === 'day' ? dateLabel(date) : `${dateLabel(from)} — ${dateLabel(shiftDate(to, -1))}`;
  return <section className="bw-surface bw-section bw-rooms" aria-label="Календарь переговорок">
    {authorized ? <>
    <div className="bw-calendar-toolbar">
      <button type="button" className="bw-button" onClick={today} title="Сегодня (T)">Сегодня</button>
      <button className="bw-button" type="button" aria-label="Предыдущий период" onClick={() => shift(-1)}>‹</button>
      <button className="bw-button" type="button" aria-label="Следующий период" onClick={() => shift(1)}>›</button>
      <h2>{title}</h2><input type="date" aria-label="Дата календаря" value={date} required onChange={e => { if (e.target.value) setDate(e.target.value); }} />
      <button type="button" className="bw-button" onClick={() => setReload(x => x + 1)}>Обновить</button>
      {data?.canWrite ? <button type="button" className="bw-button" disabled={Boolean(unresolved) || recovering} onClick={() => create()}>+ Забронировать</button> : null}
      <div className="bw-calendar-views" aria-label="Вид календаря">{(['day', 'week', 'month'] as const).map((value, index) => <button key={value} type="button" aria-pressed={view === value} onClick={() => changeView(value)} title={['День (D)', 'Неделя (W)', 'Месяц (M)'][index]}>{['День', 'Неделя', 'Месяц'][index]}</button>)}</div>
    </div>
    {data ? <div className="bw-calendar-rooms">{data.rooms.map((room, index) => <button type="button" key={room.id} className="bw-calendar-room" aria-pressed={!hidden.has(room.id)} style={{ '--room-color': roomColor(room, index) } as CSSProperties} onClick={() => {
      const next = new Set(hidden); if (next.has(room.id)) next.delete(room.id); else next.add(room.id); setHidden(next);
      try { localStorage.setItem('bw.rooms.hidden', JSON.stringify([...next])); } catch { /* Настройка необязательна. */ }
    }}><i />{room.name}</button>)}<span className="bw-calendar-hint">{data.canWrite ? 'Кликните или протяните по сетке, чтобы забронировать' : 'Только просмотр'}</span></div> : null}
    <p className="bw-calendar-note">Москва · Пн–Пт, 08:00–19:00{data ? ` · ${data.user.name}` : ''}</p>
    {notice && data ? <p className="bw-calendar-notice" role="status">{notice}</p> : null}
    {unresolved && data ? <div className="bw-calendar-notice" role="alert"><p>Предыдущая операция не подтверждена. Проверьте её результат перед новой записью. Не обновляйте страницу.</p>
      <button className="bw-button" disabled={recovering || !data.canWrite} onClick={() => void recover()}>Проверить предыдущую операцию</button></div> : null}
    {resource.status !== 'ready' ? <div className="bw-state" role={resource.status === 'loading' ? 'status' : 'alert'}><h2>{messages[resource.status][0]}</h2><p>{messages[resource.status][1]}</p>
      {resource.status === 'expired' ? <a href="/auth/basework/login">Войти</a> : null}</div> : <>
      <RoomsGrid data={resource.data} date={date} from={from} view={view} hidden={hidden} blocked={Boolean(unresolved) || recovering} scrollPosition={scrollPosition} scrollReset={scrollReset}
        open={ev => setEditing({ initial: ev, data: resource.data })} create={create} move={(ev, changes) => void move(ev, changes)} openDay={day => { setDate(day); changeView('day'); }} />
    </>}
    </> : accessPanel}
    {editing ? <BookingForm actor={actor} data={data ?? editing.data} initial={editing.initial} day={date} selected={editing.selected} csrf={csrf} suspended={!data} close={() => setEditing(null)}
      denied={() => { setEditing(null); setResource({ status: 'forbidden' }); setReload(x => x + 1); }}
      saved={message => { setEditing(null); setNotice(message); setReload(x => x + 1); }} /> : null}
  </section>;
}
