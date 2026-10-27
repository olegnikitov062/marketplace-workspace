import { useLayoutEffect, useRef, type ReactNode } from 'react';

export function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useLayoutEffect(() => {
    const node = dialog.current!;
    const previous = document.activeElement;
    node.showModal();
    node.querySelector<HTMLElement>('[data-dialog-focus]')?.focus();
    return () => {
      node.close();
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, []);
  return (
    <dialog ref={dialog} className="bw-dialog" aria-labelledby="dialog-title"
      onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close.current(); return; }
        if (event.key !== 'Tab') return;
        const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]):not([type="radio"]), input[type="radio"]:checked, [tabindex="0"]',
        )).filter(element => element.getClientRects().length > 0);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }}
      onCancel={event => { event.preventDefault(); close.current(); }}
      onClick={event => { if (event.target === event.currentTarget) {
        const rect = event.currentTarget.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close.current();
      } }}>
      <div className="bw-dialog-head"><h2 id="dialog-title">{title}</h2><button type="button" className="bw-button" onClick={onClose}>Закрыть</button></div>
      {children}
    </dialog>
  );
}
