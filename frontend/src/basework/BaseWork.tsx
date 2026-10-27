import { Component, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { Dialog } from './Dialog';
import { applicationPanel, applicationPath, directory, panels, resolveRoute, searchApplications,
  type Application, type DirectoryEntry, type PanelKind, type Resource } from './model';
import { Link, usePathname } from './navigation';
import { useBootstrap } from './useBootstrap';
import { useTheme } from './theme';
import './basework.css';

const icons: Record<string, ReactNode> = {
  chart: <path d="M4 3v17h17M8 15v-4m5 4V6m5 9v-6" />,
  file: <path d="M14 3H5v18h14V8Zm0 0v5h5M8 13h8m-8 4h5" />,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0" /></>,
  users: <><circle cx="9" cy="8" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-16a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 5v2" /></>,
  book: <path d="M3 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-2H3Zm18 0h-6a3 3 0 0 0-3 3v14a4 4 0 0 1 4-2h5Z" />,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 11h18M7 15h2m4 0h2" /></>,
  refresh: <path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5m-4 8a8 8 0 0 0 14 3l3-3m0 5v-5h-5" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  moon: <path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11Z" />,
  bell: <path d="M5 17h14l-2-3V9A5 5 0 0 0 7 9v5Zm5 4h4" />,
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
};
const applicationIcons: Record<Application['id'], string> = {
  marketplace: 'chart', reports: 'file', sources: 'database', airflow: 'refresh', bloggers: 'users', faq: 'book', rooms: 'calendar',
};
const desktopOrder = ['marketplace', 'reports', 'bloggers', 'faq', 'rooms', 'airflow', 'sources'];
function Icon({ name }: { name: string }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

function Today() {
  const now = new Date();
  const options = { timeZone: 'Europe/Moscow' } as const;
  const parts = new Intl.DateTimeFormat('ru-RU', { ...options, day: 'numeric', month: 'long' }).formatToParts(now);
  const day = parts.find(part => part.type === 'day')?.value;
  const month = parts.find(part => part.type === 'month')?.value;
  const weekday = new Intl.DateTimeFormat('ru-RU', { ...options, weekday: 'long' }).format(now);
  const date = new Intl.DateTimeFormat('sv-SE', { ...options, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
  return <time className="bw-today" dateTime={date}><strong>{day}</strong><span>{month}<br />{weekday}</span></time>;
}

function StatePanel({ kind, retry }: { kind: PanelKind; retry?: () => void }) {
  const panel = panels[kind];
  return <section className="bw-state" role={kind === 'error' || kind === 'forbidden' || kind === 'module_error' ? 'alert' : 'status'} aria-busy={kind === 'loading'}>
    <h2>{panel.title}</h2><p>{panel.description}</p>
    {retry && ['error', 'unavailable', 'module_unavailable', 'module_error', 'anonymous', 'expired', 'mfa_required', 'forbidden'].includes(kind) ?
      <button type="button" className="bw-button" onClick={retry}>Повторить проверку</button> : null}
  </section>;
}

function statusLabel(entry: DirectoryEntry) {
  return entry.access === 'unknown' ? 'Доступ не подтверждён' : entry.availability === 'unavailable' ? 'Модуль недоступен' : 'Ещё не подключено';
}

function ApplicationList({ entries }: { entries: DirectoryEntry[] }) {
  const ordered = [...entries].sort((a, b) => desktopOrder.indexOf(a.id) - desktopOrder.indexOf(b.id));
  const sources = ordered.find(entry => entry.id === 'sources');
  return <>
    <div className="bw-app-grid">{ordered.filter(entry => entry.id !== 'sources').map(entry =>
      <Link className="bw-app-link" key={entry.id} href={applicationPath(entry.id)}>
        <span className="bw-app-icon"><Icon name={applicationIcons[entry.id]} /></span>
        <span><strong>{entry.title}</strong><small>{entry.description}</small>
          {entry.access === 'allowed' && entry.availability === 'unavailable' ? <small>Модуль недоступен</small> : <span className="bw-sr-only">{statusLabel(entry)}</span>}
        </span>
      </Link>)}</div>
    {sources ? <Link className="bw-sources-link" href={applicationPath(sources.id)}>Источники данных<span className="bw-sr-only">: {statusLabel(sources)}</span></Link> : null}
  </>;
}

function SessionSummary({ resource }: { resource: Resource }) {
  if (resource.status === 'ready') return <><p className="bw-session-name">{resource.data.session.user.displayName}</p><p>Сессия подтверждена сервисом доступа.</p></>;
  if (resource.status === 'loading') return <p>Проверяем сессию…</p>;
  if (resource.status === 'error' || resource.status === 'unavailable') return <><p className="bw-session-name">Статус сессии неизвестен</p><p>Сервис доступа не вернул подтверждение.</p></>;
  return <><p className="bw-session-name">{panels[resource.status].title}</p><p>{panels[resource.status].description}</p></>;
}

function Home({ resource, retry, onSearch }: { resource: Resource; retry: () => void; onSearch: () => void }) {
  const entries = directory(resource);
  return <div className="bw-columns bw-home-columns">
    <div className="bw-surface bw-home-sheet">
      <section className="bw-home-section" aria-labelledby="work-title">
        <h2 id="work-title">Продолжить работу</h2>
        <div className="bw-work-empty"><Icon name="file" /><div><strong>Рабочие задачи пока недоступны</strong><p>Они появятся после подключения приложений.</p></div></div>
        {resource.status !== 'ready' ? <div className="bw-home-status"><StatePanel kind={resource.status} retry={retry} /></div> : null}
      </section>
      <section className="bw-home-section" aria-labelledby="applications-title">
        <div className="bw-home-section-head"><h2 id="applications-title">Приложения</h2><button type="button" className="bw-find" aria-haspopup="dialog" onClick={onSearch}>Найти <Icon name="search" /></button></div>
        {entries.length > 0 ? <><p className="bw-home-note">{resource.status === 'ready' ? 'Рабочие данные ещё не подключены.' : 'Доступ к приложениям не подтверждён.'}</p><ApplicationList entries={entries} /></> :
          resource.status === 'ready' ? <StatePanel kind="empty" /> : null}
      </section>
    </div>
    <aside className="bw-aside bw-home-aside" aria-label="Встречи и справочник">
      <section><h2>Ближайшие встречи</h2><p>Данные встреч появятся после подключения переговорок.</p>
        {entries.some(entry => entry.id === 'rooms') ? <Link href="/basework/apps/rooms">Открыть переговорки</Link> : null}</section>
      <section><h2>Найти ответственного</h2><p>Справочник поможет найти ответственного по рабочему вопросу после подключения.</p>
        {entries.some(entry => entry.id === 'faq') ? <Link href="/basework/apps/faq">Открыть справочник</Link> : null}</section>
    </aside>
  </div>;
}

function ApplicationPage({ application, resource, retry }: { application: Application; resource: Resource; retry: () => void }) {
  const kind = applicationPanel(resource, application.id);
  return <div className="bw-columns">
    <div className="bw-surface"><StatePanel kind={kind} retry={retry} />
      <div className="bw-section-footer"><Link href="/basework/">На рабочий стол</Link><Link href="/basework/profile">Проверить сессию</Link></div>
    </div>
    <aside className="bw-aside"><section><h2>О разделе</h2><p>{application.description}</p>
      <p>{application.id === 'airflow' ? 'Предусмотрен только просмотр. Запуск процессов из BaseWork не поддерживается.' : 'Рабочие данные и процессы остаются в существующем приложении.'}</p>
      {resource.status === 'ready' && kind === 'not_connected' ? <p>Доступ подтверждён. Подключение данных модуля ещё не выполнено.</p> : null}
    </section></aside>
  </div>;
}

function Profile({ resource, retry, logout }: { resource: Resource; retry: () => void; logout: (all: boolean) => Promise<void> }) {
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  const leave = async (all: boolean) => {
    setPending(true);
    setMessage('');
    try {
      await logout(all);
      setMessage(all ? 'Все сессии BaseWork завершены. Сессия провайдера входа может оставаться активной.' :
        'Сессия BaseWork завершена. Сессия провайдера входа может оставаться активной.');
    } catch { setMessage('Сервер не подтвердил выход. Проверяем состояние сессии; при необходимости повторите выход.'); }
    finally { setPending(false); }
  };
  return <div className="bw-columns"><section className="bw-surface bw-section" aria-labelledby="session-title">
    <h2 id="session-title">Текущая сессия</h2><SessionSummary resource={resource} />
    {resource.status === 'ready' ? <p>Разрешения приложений определяет сервер. Настройки темы не влияют на доступ.</p> : null}
    <button type="button" className="bw-button" onClick={retry} disabled={pending || resource.status === 'loading'}>{resource.status === 'loading' ? 'Проверяем сессию…' : 'Проверить сессию'}</button>
    <div className="bw-section-footer">
      {resource.status === 'ready' || resource.status === 'mfa_required' || pending ? <>
        <button type="button" className="bw-button" disabled={pending} onClick={() => void leave(false)}>Выйти</button>
        {resource.status === 'ready' ? <button type="button" className="bw-button" disabled={pending} onClick={() => void leave(true)}>Выйти из всех сессий</button> : null}
      </> : null}
      {['anonymous', 'expired'].includes(resource.status) ?
        <a className="bw-button" href="/auth/mfa/login/">Вход Marketplace с MFA</a> : null}
      {resource.status === 'mfa_required' ? <a className="bw-button" href="/auth/mfa/setup/">Завершить настройку MFA</a> : null}
      {resource.status === 'ready' ? <a href="/auth/security/">Безопасность и подтверждение MFA</a> : null}
    </div>
    <p role="status" aria-live="polite">{pending ? 'Сервер завершает сессию…' : message}</p>
  </section><aside className="bw-aside"><section><h2>Общий вход</h2><p>Authelia пока не подключена. Доступен существующий вход Marketplace; его проверки MFA сохраняются.</p><p>Выход из BaseWork не подтверждает выход из Authelia или отдельных приложений.</p></section></aside></div>;
}

function Notifications() {
  return <section className="bw-surface bw-section" aria-labelledby="notifications-title">
    <h2 id="notifications-title">Пока нет уведомлений</h2><p className="bw-muted">Источник событий ещё не подключён. Здесь появятся уведомления о реальных событиях.</p>
  </section>;
}

function Search({ entries, onNavigate }: { entries: DirectoryEntry[]; onNavigate: () => void }) {
  const [query, setQuery] = useState('');
  const results = searchApplications(entries, query);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  return <>
    <label className="bw-search-label" htmlFor="app-search">Название или задача</label>
    <input ref={input} data-dialog-focus id="app-search" type="search" name="application-search" autoComplete="off" spellCheck={false}
      placeholder="Например, справочник…" value={query} onChange={event => setQuery(event.target.value)}
      onKeyDown={event => { if (event.key === 'ArrowDown') { event.preventDefault(); list.current?.querySelector<HTMLAnchorElement>('a')?.focus(); } }} />
    <p className="bw-search-result" role="status">{results.length ? `Найдено приложений: ${results.length}` : 'Ничего не найдено'}</p>
    {results.some(entry => entry.access === 'unknown') ? <p className="bw-muted">Поиск по составу BaseWork. Доступ к этим разделам пока не подтверждён.</p> : null}
    <div ref={list} className="bw-search-list">
      {results.length ? results.map(entry => <Link className="bw-search-link" key={entry.id} href={applicationPath(entry.id)} onClick={onNavigate}>
        <strong>{entry.title}</strong><span>{entry.description}</span><small>{statusLabel(entry)}</small>
      </Link>) : <p className="bw-muted">{entries.length ? 'Попробуйте другое название или задачу.' : 'Нет подтверждённых приложений для текущей сессии.'}</p>}
    </div>
    {query ? <button type="button" className="bw-button" onClick={() => { setQuery(''); input.current?.focus(); }}>Очистить поиск</button> : null}
  </>;
}

class ModuleBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="bw-surface"><StatePanel kind="module_error" retry={() => this.setState({ failed: false })} /></div> : this.props.children;
  }
}

type OpenDialog = 'search' | 'theme' | 'menu' | null;
export function BaseWork() {
  const pathname = usePathname();
  const route = resolveRoute(pathname);
  const { resource, retry, logout } = useBootstrap();
  const entries = directory(resource);
  const { preference, choose } = useTheme();
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const title = route.kind === 'application' ? route.application.title :
    { home: 'Рабочий стол', profile: 'Профиль', notifications: 'Уведомления', missing: 'Страница не найдена' }[route.kind];
  const description = route.kind === 'application' ? route.application.description :
    { home: 'Приложения и ближайшие дела.', profile: 'Состояние входа и доступа к приложениям.', notifications: 'События рабочих приложений.', missing: 'Этот адрес не относится к доступным страницам BaseWork.' }[route.kind];
  useLayoutEffect(() => {
    setDialog(null);
    document.title = `${title} — BaseWork`;
    heading.current?.focus();
    window.scrollTo(0, 0);
  }, [pathname]);
  useEffect(() => {
    const openSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && !event.isComposing) {
        event.preventDefault(); setDialog('search');
      }
    };
    window.addEventListener('keydown', openSearch);
    return () => window.removeEventListener('keydown', openSearch);
  }, []);
  const closeDialog = () => setDialog(null);
  const navigationEntries = [...entries].sort((a, b) => {
    const order = ['marketplace', 'reports', 'bloggers', 'faq', 'rooms', 'sources', 'airflow'];
    return order.indexOf(a.id) - order.indexOf(b.id);
  });
  const navigation = <><Link href="/basework/" aria-label="Рабочий стол" aria-current={route.kind === 'home' ? 'page' : undefined} onClick={closeDialog}>Стол</Link>
    {navigationEntries.map(entry => <Link key={entry.id} href={applicationPath(entry.id)} onClick={closeDialog} aria-label={entry.title}
      aria-current={route.kind === 'application' && route.application.id === entry.id ? 'page' : undefined}>{entry.id === 'sources' ? 'Данные' : entry.title}</Link>)}</>;
  return <div className="bw-suite">
    <a className="bw-skip" href="#main-content">К содержимому</a>
    <header className="bw-topbar">
      <button type="button" className="bw-top-action bw-menu" aria-label="Меню" aria-haspopup="dialog" onClick={() => setDialog('menu')}><Icon name="menu" /></button>
      <Link href="/basework/" className="bw-brand" aria-label="BaseWork, рабочий стол"><span className="bw-brand-mark" aria-hidden="true"><i /><i /><i /></span><span translate="no">BaseWork</span></Link>
      <nav className="bw-desktop-nav" aria-label="Приложения BaseWork">{navigation}</nav>
      <div className="bw-actions">
        <button type="button" className="bw-top-search" aria-label="Поиск" aria-haspopup="dialog" aria-keyshortcuts="Control+k Meta+k" onClick={() => setDialog('search')}><Icon name="search" /><span className="bw-search-caption">Поиск</span><span className="bw-shortcut" aria-hidden="true">Ctrl K</span></button>
        <button type="button" className="bw-top-action" aria-label="Тема" aria-haspopup="dialog" onClick={() => setDialog('theme')}><Icon name="moon" /></button>
        <Link className="bw-top-action bw-notification-action" href="/basework/notifications" aria-label="Уведомления" aria-current={route.kind === 'notifications' ? 'page' : undefined}><Icon name="bell" /></Link>
        <Link className="bw-profile-action" href="/basework/profile" aria-label="Профиль" aria-current={route.kind === 'profile' ? 'page' : undefined}><span className="bw-profile-icon"><Icon name="users" /></span><span>Профиль</span></Link>
      </div>
    </header>
    <main id="main-content" className="bw-main" tabIndex={-1}>
      <div className="bw-page-head"><div><h1 ref={heading} tabIndex={-1}>{title}</h1><p>{description}</p></div>
        {route.kind === 'home' ? <Today /> : null}
      </div>
      <ModuleBoundary key={pathname}>
        {route.kind === 'home' ? <Home resource={resource} retry={retry} onSearch={() => setDialog('search')} /> :
          route.kind === 'profile' ? <Profile resource={resource} retry={retry} logout={logout} /> :
          route.kind === 'notifications' ? <Notifications /> :
          route.kind === 'application' ? <ApplicationPage application={route.application} resource={resource} retry={retry} /> :
          <div className="bw-surface"><StatePanel kind="missing" /><div className="bw-section-footer"><Link href="/basework/">На рабочий стол</Link></div></div>}
      </ModuleBoundary>
    </main>
    <footer className="bw-footer"><span translate="no">BaseWork</span><span>Подключение приложений выполняется поэтапно.</span></footer>
    {dialog ? <Dialog key={dialog} title={{ search: 'Поиск приложений', theme: 'Тема оформления', menu: 'Приложения BaseWork' }[dialog]} onClose={closeDialog}>
      {dialog === 'search' ? <Search entries={entries} onNavigate={closeDialog} /> : dialog === 'menu' ? <>
        {resource.status !== 'ready' ? <p className="bw-muted">{resource.status === 'error' || resource.status === 'unavailable' ? 'Доступ к разделам не подтверждён.' : panels[resource.status].title}</p> : null}
        <nav className="bw-mobile-nav" aria-label="Навигация по разделам">{navigation}<Link href="/basework/profile" onClick={closeDialog}>Профиль</Link><Link href="/basework/notifications" onClick={closeDialog}>Уведомления</Link></nav>
      </> : <fieldset className="bw-theme-options"><legend>Выберите оформление</legend>
        {([['system', 'Как в системе'], ['light', 'Светлая'], ['dark', 'Тёмная']] as const).map(([value, label]) =>
          <label key={value}><input type="radio" name="theme" value={value} checked={preference === value} onChange={() => choose(value)} />{label}</label>)}
        <p className="bw-muted">Выбор сохраняется только в этом браузере.</p>
      </fieldset>}
    </Dialog> : null}
  </div>;
}
