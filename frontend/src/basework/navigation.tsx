import { useSyncExternalStore, type AnchorHTMLAttributes, type MouseEvent } from 'react';

const changed = 'basework:navigation';
const snapshot = () => window.location.pathname;
function subscribe(onChange: () => void) {
  window.addEventListener('popstate', onChange);
  window.addEventListener(changed, onChange);
  return () => {
    window.removeEventListener('popstate', onChange);
    window.removeEventListener(changed, onChange);
  };
}
export function usePathname() { return useSyncExternalStore(subscribe, snapshot, () => '/basework/'); }

export function Link({ href, onClick, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  function follow(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event);
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
        props.target || props.download !== undefined) return;
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin || (url.pathname !== '/basework/' && !url.pathname.startsWith('/basework/'))) return;
    event.preventDefault();
    if (url.href === window.location.href) return;
    window.history.pushState(null, '', url.pathname + url.search + url.hash);
    window.dispatchEvent(new Event(changed));
  }
  return <a {...props} href={href} onClick={follow} />;
}
