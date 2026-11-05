import type { MouseEvent } from 'react';
import { Link } from './navigation';
import type { ThemePreference } from './theme';

type Props = {
  name: string;
  preference: ThemePreference;
  choose: (theme: ThemePreference) => void;
  onSearch: () => void;
  onProfile: () => void;
  profileOpen?: boolean;
  showProfile?: boolean;
  showSearch?: boolean;
  onHome?: (event: MouseEvent<HTMLAnchorElement>) => void;
};

function HeaderIcon({ name }: { name: 'search' | 'sun' | 'moon' | 'chevron' }) {
  const paths = {
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></>,
    moon: <path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11Z" />,
    chevron: <path d="m6 9 6 6 6-6" />,
  };
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export function WorkspaceHeader({ name, preference, choose, onSearch, onProfile, profileOpen = false, showProfile = true, showSearch = true, onHome }: Props) {
  const displayName = name.trim() || 'Профиль';
  const initial = Array.from(displayName)[0].toLocaleUpperCase('ru-RU');
  return <header className="workspace-header">
    <Link className="workspace-mark" href="/basework/" aria-label="BaseWork, рабочий стол" onClick={onHome}><span aria-hidden="true"><i /><i /><i /></span></Link>
    <Link className="workspace-brand" href="/basework/" onClick={onHome} translate="no">BaseWork</Link>
    <div className="workspace-actions">
      {showSearch && <button type="button" className="workspace-search" onClick={onSearch} aria-label="Найти приложение" aria-haspopup="dialog" aria-keyshortcuts="Control+k Meta+k"><HeaderIcon name="search" /><span>Найти приложение</span><kbd>Ctrl K</kbd></button>}
      <div className="workspace-theme" role="group" aria-label="Тема оформления">
        <button type="button" aria-label="Светлая тема" title="Светлая тема" aria-pressed={preference === 'light'} onClick={() => choose('light')}><HeaderIcon name="sun" /></button>
        <button type="button" aria-label="Тёмная тема" title="Тёмная тема" aria-pressed={preference === 'dark'} onClick={() => choose('dark')}><HeaderIcon name="moon" /></button>
      </div>
      {showProfile && <span className="workspace-divider" aria-hidden="true" />}
      {showProfile && <button type="button" className="workspace-profile" aria-expanded={profileOpen} aria-label={'Меню профиля, ' + displayName} aria-haspopup="dialog" onClick={onProfile}><span className="workspace-avatar" aria-hidden="true">{initial}</span><span className="workspace-name">{displayName}</span><HeaderIcon name="chevron" /></button>}
    </div>
  </header>;
}
