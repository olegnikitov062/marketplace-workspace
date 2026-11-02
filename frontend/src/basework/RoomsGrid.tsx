import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent } from 'react';
import { atMinute, layoutBookings, minuteTime, moscowDate, moscowTime, shiftDate, weekDay, roomColor,
  type Booking, type CalendarData, type CalendarView } from './roomsApi';

export type Slot = { date: string; start: string; end: string; roomId?: string };
type Column = { day: string; roomId?: string; name: string };
type Selection = { column: number; start: number; end: number };
type Gesture = { mode: 'select' | 'move' | 'resize'; column: number; anchor: number; offset: number;
  ev?: Booking; x: number; y: number; moved: boolean; selection: Selection };
const HOUR = 48;
const label = (day: string) => new Intl.DateTimeFormat('ru-RU', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(day + 'T12:00:00Z'));

export function RoomsGrid({ data, date, from, view, hidden, blocked, open, create, move, openDay, scrollPosition, scrollReset }: {
  data: CalendarData; date: string; from: string; view: CalendarView; hidden: Set<string>; blocked: boolean;
  open: (ev: Booking) => void; create: (slot: Slot) => void;
  move: (ev: Booking, changes: { start: string; end: string; roomId: string }) => void; openDay: (day: string) => void;
  scrollPosition: { current: number }; scrollReset: number;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const elements = useRef(new Map<number, HTMLDivElement>());
  const gesture = useRef<Gesture | null>(null);
  const suppress = useRef(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const rooms = data.rooms.filter(room => !hidden.has(room.id));
  const events = data.events.filter(ev => !hidden.has(ev.roomId));
  const today = moscowDate();
  const columns: Column[] = view === 'day' ? rooms.map(room => ({ day: date, roomId: room.id, name: room.name })) :
    Array.from({ length: 7 }, (_, i) => ({ day: shiftDate(from, i), name: label(shiftDate(from, i)) }));
  useLayoutEffect(() => { if (scroller.current) scroller.current.scrollTop = scrollPosition.current; }, [view, from, rooms.length, scrollReset, scrollPosition]);
  useEffect(() => {
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !gesture.current) return;
      event.preventDefault(); gesture.current = null; suppress.current = true; setSelection(null);
    };
    document.addEventListener('keydown', cancel);
    return () => document.removeEventListener('keydown', cancel);
  }, []);
  useEffect(() => { gesture.current = null; setSelection(null); }, [view, from, date, hidden]);
  const color = (id: string) => { const index = data.rooms.findIndex(r => r.id === id); return roomColor(data.rooms[index], index); };
  const canCreate = data.canWrite && !blocked;
  const permitted = (column: number) => canCreate && ![0, 6].includes(weekDay(columns[column].day));
  const minute = (column: number, y: number) => Math.max(0, Math.min(1440, (y - elements.current.get(column)!.getBoundingClientRect().top) / HOUR * 60));
  const slot = (column: number, start: number, end: number): Slot => ({ date: columns[column].day, start: minuteTime(start), end: minuteTime(end), roomId: columns[column].roomId });
  const startGesture = (event: PointerEvent<HTMLElement>, column: number, ev?: Booking, resize = false) => {
    event.stopPropagation();
    suppress.current = false;
    if (event.pointerType !== 'mouse' || event.button !== 0 || !canCreate || (ev && (!ev.canEdit || !permitted(column)))) return;
    event.preventDefault();
    const anchor = Math.max(480, Math.min(1125, Math.floor(minute(column, event.clientY) / 15) * 15));
    const midnight = Date.parse(columns[column].day + 'T00:00:00+03:00');
    const start = ev ? (Date.parse(ev.start) - midnight) / 60000 : anchor;
    const end = ev ? (Date.parse(ev.end) - midnight) / 60000 : Math.min(anchor + 60, 1140);
    const current = { column, start, end };
    gesture.current = { mode: ev ? resize ? 'resize' : 'move' : 'select', column, anchor,
      offset: minute(column, event.clientY) - start, ev, x: event.clientX, y: event.clientY, moved: false, selection: current };
    if (!ev) setSelection(current);
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const update = (event: PointerEvent) => {
    const current = gesture.current;
    if (!current) return;
    if (Math.abs(event.clientX - current.x) + Math.abs(event.clientY - current.y) >= 4) current.moved = true;
    if (!current.moved) return;
    let column = current.column, start: number, end: number;
    if (current.mode === 'move') {
      const found = [...elements.current].find(([, element]) => { const rect = element.getBoundingClientRect(); return event.clientX >= rect.left && event.clientX < rect.right; });
      column = found?.[0] ?? column;
      if (!permitted(column)) return;
      const duration = (Date.parse(current.ev!.end) - Date.parse(current.ev!.start)) / 60000;
      start = Math.max(480, Math.min(1140 - duration, Math.round((minute(column, event.clientY) - current.offset) / 15) * 15));
      end = start + duration;
    } else if (current.mode === 'resize') {
      start = current.selection.start;
      end = Math.max(start + 15, Math.min(1140, Math.round(minute(column, event.clientY) / 15) * 15));
    } else {
      const endMinute = Math.max(480, Math.min(1125, Math.floor(minute(column, event.clientY) / 15) * 15));
      start = Math.min(current.anchor, endMinute); end = Math.max(current.anchor, endMinute) + 15;
    }
    current.selection = { column, start, end }; setSelection(current.selection);
  };
  const finish = (cancel = false) => {
    const current = gesture.current;
    gesture.current = null; setSelection(null);
    if (!current) return;
    if (current.mode !== 'select' && !current.moved) return;
    suppress.current = true; window.setTimeout(() => { suppress.current = false; }, 0);
    if (cancel || blocked || !data.canWrite) return;
    const { column, start, end } = current.selection;
    if (current.mode === 'select') {
      const clickStart = Math.min(1080, Math.floor(start / 30) * 30);
      create(slot(column, current.moved ? start : clickStart, current.moved ? end : clickStart + 60));
    }
    else {
      if (!permitted(column)) return;
      const changes = { start: atMinute(columns[column].day, start), end: atMinute(columns[column].day, end), roomId: columns[column].roomId ?? current.ev!.roomId };
      if (Date.parse(changes.start) !== Date.parse(current.ev!.start) || Date.parse(changes.end) !== Date.parse(current.ev!.end) || changes.roomId !== current.ev!.roomId) move(current.ev!, changes);
    }
  };

  if (!rooms.length) return <p className="bw-state">Выберите хотя бы одну переговорку выше.</p>;
  if (view === 'month') return <div className="bw-calendar-month" aria-label="Календарь на месяц">
    {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => <div key={day} className="bw-month-heading">{day}</div>)}
    {Array.from({ length: 42 }, (_, i) => shiftDate(from, i)).map(day => {
      const items = layoutBookings(events, day);
      const count = items.length > 3 ? 2 : 3;
      return <section key={day} className={`bw-month-cell${day.slice(0, 7) !== date.slice(0, 7) ? ' other' : ''}${day === today ? ' today' : ''}`} aria-label={label(day)}
        onClick={event => { if (!(event.target as HTMLElement).closest('button') && canCreate) create({ date: day, start: '10:00', end: '11:00' }); }}>
        <button className="bw-month-date" onClick={() => openDay(day)} title="Открыть день">{Number(day.slice(8))}</button>
        {items.slice(0, count).map(({ ev }) => <button key={ev.id} className="bw-month-event" disabled={blocked} style={{ '--room-color': color(ev.roomId) } as CSSProperties} onClick={() => open(ev)} title={`${ev.title}, ${moscowTime(ev.start)}–${moscowTime(ev.end)}`}><span>{moscowTime(ev.start)}</span> {ev.seriesId ? '↻ ' : ''}{ev.title}</button>)}
        {items.length > count ? <button className="bw-month-more" onClick={() => openDay(day)}>ещё {items.length - count}</button> : null}
        {canCreate ? <button className="bw-month-add" aria-label={`Забронировать ${label(day)}`} onClick={() => create({ date: day, start: '10:00', end: '11:00' })}>+</button> : null}
      </section>;
    })}
  </div>;
  const template = `56px repeat(${columns.length}, minmax(${view === 'week' ? '96px' : '120px'}, 1fr))`;
  return <div className="bw-calendar-grid" ref={scroller} aria-label={view === 'day' ? 'Время и переговорки' : 'Время и дни недели'}
    onScroll={event => { scrollPosition.current = event.currentTarget.scrollTop; }}
    onPointerMove={update} onPointerUp={() => finish()} onPointerCancel={() => finish(true)}>
    <div className="bw-calendar-head" style={{ gridTemplateColumns: template }}><div aria-hidden="true" />{columns.map((column, i) =>
      <div className={column.day === today ? 'today' : ''} key={column.roomId ?? column.day}>
        {view === 'day' ? <span><i style={{ background: color(column.roomId!) }} />{column.name}</span> : <button onClick={() => openDay(column.day)} title="Открыть день">{column.name}</button>}
        <span className="bw-sr-only">Колонка {i + 1}</span>
      </div>)}</div>
    <div className="bw-calendar-hours" style={{ gridTemplateColumns: template }}>
      <div className="bw-calendar-gutter">{Array.from({ length: 23 }, (_, i) => i + 1).map(hour => <span key={hour} style={{ top: hour * HOUR }}>{minuteTime(hour * 60)}</span>)}</div>
      {columns.map((column, index) => <div key={column.roomId ?? column.day} ref={node => { if (node) elements.current.set(index, node); else elements.current.delete(index); }}
        className={`bw-calendar-column${[0, 6].includes(weekDay(column.day)) ? ' weekend' : ''}`} onPointerDown={event => startGesture(event, index)}
        onClick={event => { if (suppress.current || !canCreate) return; if (event.detail === 0) return; const start = Math.max(480, Math.min(1080, Math.floor(minute(index, event.clientY) / 30) * 30)); create(slot(index, start, start + 60)); }}>
        {layoutBookings(events, column.day, column.roomId).map(({ ev, start, end, column: lane, columns: lanes }) =>
          <button key={ev.id} type="button" className={`bw-calendar-event${end - start < 45 ? ' compact' : ''}`} disabled={blocked}
            style={{ top: start / 60 * HOUR, height: Math.max((end - start) / 60 * HOUR - 2, 18), left: `calc(${lane / lanes * 100}% + 2px)`, width: `calc(${100 / lanes}% - 4px)`, '--room-color': color(ev.roomId) } as CSSProperties}
            aria-label={`${ev.title}, ${moscowTime(ev.start)}–${moscowTime(ev.end)}, ${data.rooms.find(r => r.id === ev.roomId)?.name}`}
            title={`${ev.title}\n${moscowTime(ev.start)}–${moscowTime(ev.end)}\n${ev.canEdit && data.canWrite ? 'Перетащите для переноса; нижний край изменяет длительность' : 'Только просмотр'}`}
            onPointerDown={event => startGesture(event, index, ev, (event.target as HTMLElement).classList.contains('bw-calendar-resize'))}
            onClick={event => { event.stopPropagation(); if (!suppress.current) open(ev); }}>
            <strong>{ev.seriesId ? '↻ ' : ''}{ev.title}</strong><span>{end - start < 45 ? moscowTime(ev.start) : `${moscowTime(ev.start)}–${moscowTime(ev.end)}`}{view === 'week' && end - start >= 45 ? ` · ${data.rooms.find(r => r.id === ev.roomId)?.name}` : ''}</span>
            {ev.canEdit && data.canWrite && end < 1440 ? <span className="bw-calendar-resize" aria-hidden="true" /> : null}
          </button>)}
        {column.day === today ? <div className="bw-calendar-now" style={{ top: ((Date.now() - Date.parse(today + 'T00:00:00+03:00')) / 60000) / 60 * HOUR }} /> : null}
        {selection?.column === index ? <div className="bw-calendar-selection" style={{ top: selection.start / 60 * HOUR, height: (selection.end - selection.start) / 60 * HOUR }}>{minuteTime(selection.start)}–{minuteTime(selection.end)}</div> : null}
      </div>)}
    </div>
  </div>;
}
