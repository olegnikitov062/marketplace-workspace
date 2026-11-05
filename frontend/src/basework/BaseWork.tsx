import { Component, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { Dialog } from './Dialog';
import { Faq } from './Faq';
import { Rooms } from './Rooms';
import { applicationPanel, applicationPath, directory, panels, resolveRoute, searchApplications,
  type Application, type DirectoryEntry, type PanelKind, type Resource } from './model';
import { Link, usePathname } from './navigation';
import { useBootstrap } from './useBootstrap';
import { useTheme } from './theme';
import { useAuthOptions } from './useAuthOptions';
import { oidcLoginPath } from './authOptions';
import './basework.css';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceIcon } from './WorkspaceIcon';
import { workspaceDescriptions, workspaceOrder } from './workspaceCatalog';

const icons: Record<string, ReactNode> = {
  home: <path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" />,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1" /></>,
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
  return <time className="bw-today" dateTime={date}><WorkspaceIcon name="calendar" size={18} /><span>{weekday.charAt(0).toLocaleUpperCase('ru-RU') + weekday.slice(1)}, {day} {month}</span></time>;
}

function StatePanel({ kind, retry }: { kind: PanelKind; retry?: () => void }) {
  const panel = panels[kind];
  return <section className="bw-state" role={kind === 'error' || kind === 'forbidden' || kind === 'module_error' ? 'alert' : 'status'} aria-busy={kind === 'loading'}>
    <h2>{panel.title}</h2><p>{panel.description}</p>
    {['anonymous', 'expired'].includes(kind) ? <a className="bw-button" href="/auth/basework/login">Войти</a> : null}
    {retry && ['error', 'unavailable', 'module_unavailable', 'module_error', 'mfa_required', 'forbidden'].includes(kind) ?
      <button type="button" className="bw-button" onClick={retry}>Повторить проверку</button> : null}
  </section>;
}

function statusLabel(entry: DirectoryEntry) {
  return entry.access === 'unknown' ? 'Доступ не подтверждён' : entry.availability === 'unavailable' ? 'Модуль недоступен' : entry.id === 'faq' ? 'Доступен для чтения' : entry.id === 'rooms' ? 'Открыть календарь' : 'Ещё не подключено';
}

function ApplicationList({ entries }: { entries: DirectoryEntry[] }) {
  const ordered = [...entries].sort((a, b) => workspaceOrder.indexOf(a.id) - workspaceOrder.indexOf(b.id));
  return <>
    <div className="bw-app-grid">{ordered.map(entry =>
      <Link className="bw-app-link" key={entry.id} href={applicationPath(entry.id)}>
        <span className="bw-app-icon"><WorkspaceIcon name={entry.id} /></span>
        <span><strong>{entry.id === 'faq' ? 'Справочник команды' : entry.title}</strong><small>{workspaceDescriptions[entry.id]}</small>
          {entry.access === 'allowed' && entry.availability === 'unavailable' ? <small>Модуль недоступен</small> : <span className="bw-sr-only">{statusLabel(entry)}</span>}
        </span>
      </Link>)}</div>

  </>;
}

function SessionSummary({ resource }: { resource: Resource }) {
  if (resource.status === 'ready') return <><p className="bw-session-name">Логин: {resource.data.session.user.displayName}</p><p>Сессия подтверждена сервисом доступа.</p></>;
  if (resource.status === 'loading') return <p>Проверяем сессию…</p>;
  if (resource.status === 'error' || resource.status === 'unavailable') return <><p className="bw-session-name">Статус сессии неизвестен</p><p>Сервис доступа не вернул подтверждение.</p></>;
  return <><p className="bw-session-name">{panels[resource.status].title}</p><p>{panels[resource.status].description}</p></>;
}

function Home({ resource, retry }: { resource: Resource; retry: () => void }) {
  const entries = directory(resource);
  const rooms = entries.find(entry => entry.id === 'rooms' && entry.access === 'allowed');
  return <div className="bw-workspace">
    {resource.status !== 'ready' ? <div className="bw-surface"><StatePanel kind={resource.status} retry={retry} /></div> : null}
    {rooms ? <section className="bw-meeting-hero" aria-label="Переговорки">
      <div className="bw-meeting-map"><h2>Переговорки</h2><div className="bw-meeting-art" role="img" aria-label="Условная схема двух переговорок" /><span className="workspace-room-label workspace-room-large">Большая</span><span className="workspace-room-label workspace-room-small">Малая</span><small><WorkspaceIcon name="map" size={15} />Условная схема офиса</small></div>
      <div className="bw-meeting-agenda"><h2>Расписание встреч</h2><p><span>Занятость комнат и ваши встречи</span><span>доступны в приложении переговорок.</span></p><Link className="bw-button" href={applicationPath(rooms.id)}>Открыть календарь</Link></div>
    </section> : null}
    <section aria-labelledby="applications-title">
      <div className="bw-home-section-head"><h2 id="applications-title">Приложения</h2></div>
      {entries.length > 0 ? <ApplicationList entries={entries} /> : resource.status === 'ready' ? <div className="bw-surface"><StatePanel kind="empty" /></div> : null}
    </section>
  </div>;
}

function RoomsPage({ resource, retry }: { resource: Resource; retry: () => void }) {
  const [identity, setIdentity] = useState<{ actor: string; csrf: string } | null>(null);
  const allowed = resource.status === 'ready' && resource.data.applications.some(item => item.id === 'rooms' && item.access === 'allowed');
  // Временная проверка скрывает модуль, но не уничтожает черновик. Отказ и смена
  // пользователя сбрасывают его до показа следующего кадра.
  if (allowed && resource.status === 'ready') {
    const actor = resource.data.session.user.id, csrf = resource.data.csrfToken ?? '';
    if (identity?.actor !== actor || identity.csrf !== csrf) setIdentity({ actor, csrf });
  } else if (identity && !['loading', 'error', 'unavailable'].includes(resource.status)) {
    setIdentity(null);
  }
  const panel = <StatePanel kind={applicationPanel(resource, 'rooms')} retry={retry} />;
  return identity ? <Rooms key={identity.actor} actor={identity.actor} csrf={identity.csrf} authorized={allowed} accessPanel={panel} /> : panel;
}

function ApplicationPage({ application, resource, retry }: { application: Application; resource: Resource; retry: () => void }) {
  const kind = applicationPanel(resource, application.id);
  if (application.id === 'rooms') return <RoomsPage resource={resource} retry={retry} />;
  if (application.id === 'faq' && resource.status === 'ready' &&
      resource.data.applications.some(item => item.id === 'faq' && item.access === 'allowed')) {
    return <Faq key={resource.data.session.user.id} />;
  }
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
  const authOptions = useAuthOptions();
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
    <div className="bw-profile-actions">
      <button type="button" className="bw-button" onClick={retry} disabled={pending || resource.status === 'loading'}>{resource.status === 'loading' ? 'Проверяем сессию…' : 'Проверить сессию'}</button>
      {resource.status === 'ready' || resource.status === 'mfa_required' || pending ? <>
        <button type="button" className="bw-button" disabled={pending} onClick={() => void leave(false)}>Выйти</button>
        {resource.status === 'ready' ? <button type="button" className="bw-button" disabled={pending} onClick={() => void leave(true)}>Выйти из всех сессий</button> : null}
      </> : null}
      {['anonymous', 'expired'].includes(resource.status) ?
        <><a className="bw-button" href="/auth/basework/login">Войти по логину и паролю</a>
          {authOptions === 'enabled' ? <a href={oidcLoginPath}>Войти через Authelia</a> : null}</> : null}
      {resource.status === 'mfa_required' ? <a className="bw-button" href="/auth/mfa/setup/">Завершить настройку MFA</a> : null}
      {resource.status === 'ready' ? <a href="/auth/security/">Безопасность и подтверждение MFA</a> : null}
      {resource.status === 'ready' && resource.data.canManageUsers ? <a className="bw-button" href="/auth/basework/users/">Управление пользователями</a> : null}
    </div>
    <p role="status" aria-live="polite">{pending ? 'Сервер завершает сессию…' : message}</p>
  </section><aside className="bw-aside"><section><h2>Вход в аккаунт</h2>
    <p>Используйте свой логин и пароль. После входа откроется рабочий стол.</p>
    {authOptions === 'enabled' ? <p>Также доступен вход через Authelia. Выход из BaseWork не завершает сессию Authelia.</p> : null}
  </section></aside></div>;
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

type OpenDialog = 'search' | 'theme' | 'menu' | 'profile' | null;
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
  const navigation = navigationEntries.map(entry => <Link key={entry.id} href={applicationPath(entry.id)} onClick={closeDialog} aria-label={entry.title}
    aria-current={route.kind === 'application' && route.application.id === entry.id ? 'page' : undefined}><Icon name={applicationIcons[entry.id]} /><span>{entry.id === 'sources' ? 'Данные' : entry.title}</span></Link>);
  return <div className="bw-suite">
    <a className="bw-skip" href="#main-content">К содержимому</a>
    <WorkspaceHeader name={resource.status === 'ready' ? resource.data.session.user.displayName : ''}
      preference={preference} choose={choose} profileOpen={dialog === 'profile'} onSearch={() => setDialog('search')} onProfile={() => setDialog('profile')} />
    <nav className="bw-rail" aria-label="Приложения BaseWork"><Link href="/basework/" aria-label="Рабочий стол" title="Рабочий стол" aria-current={route.kind === 'home' ? 'page' : undefined}><WorkspaceIcon name="home" size={23} /></Link>{navigationEntries.map(entry => <Link key={entry.id} href={applicationPath(entry.id)} aria-label={entry.title} title={entry.title} aria-current={route.kind === 'application' && route.application.id === entry.id ? 'page' : undefined}><WorkspaceIcon name={entry.id} /></Link>)}<Link className="workspace-notifications" href="/basework/notifications" title="Уведомления" aria-label="Уведомления" aria-current={route.kind === 'notifications' ? 'page' : undefined}><Icon name="bell" /></Link></nav>
    <main id="main-content" className="bw-main" tabIndex={-1}>
      <div className="bw-page-head"><div><h1 ref={heading} tabIndex={-1}>{title}</h1>{route.kind !== 'home' ? <p>{description}</p> : null}</div>
        {route.kind === 'home' ? <Today /> : null}
      </div>
      <ModuleBoundary key={pathname}>
        {route.kind === 'home' ? <Home resource={resource} retry={retry} /> :
          route.kind === 'profile' ? <Profile resource={resource} retry={retry} logout={logout} /> :
          route.kind === 'notifications' ? <Notifications /> :
          route.kind === 'application' ? <ApplicationPage application={route.application} resource={resource} retry={retry} /> :
          <div className="bw-surface"><StatePanel kind="missing" /><div className="bw-section-footer"><Link href="/basework/">На рабочий стол</Link></div></div>}
      </ModuleBoundary>
    </main>

    {dialog ? <Dialog key={dialog} title={{ search: 'Поиск приложений', theme: 'Тема оформления', menu: 'Приложения BaseWork', profile: 'Профиль' }[dialog]} onClose={closeDialog}>
      {dialog === 'profile' ? <div className="bw-profile-menu">
        <SessionSummary resource={resource} />
        <Link data-dialog-focus className="bw-button" href="/basework/profile" onClick={closeDialog}>Профиль и безопасность</Link>
        <Link className="bw-button" href="/basework/notifications" onClick={closeDialog}>Уведомления</Link>
        <button type="button" className="bw-button" onClick={() => setDialog('theme')}>Настройки темы</button>
      </div> : dialog === 'search' ? <Search entries={entries} onNavigate={closeDialog} /> : dialog === 'menu' ? <>
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
