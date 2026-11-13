import React, { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { PanelsTopLeft, X } from 'lucide-react';

const openDialogs: HTMLDivElement[] = [];

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const previousOverflow = document.body.style.overflow;
    const root = document.getElementById('root');
    const rootWasInert = root?.inert ?? false;
    if (root) root.inert = true;
    document.body.style.overflow = 'hidden';
    const dialog = ref.current;
    if (dialog) openDialogs.push(dialog);
    ref.current?.focus({ preventScroll: true });
    const handler = (event: KeyboardEvent) => {
      if (openDialogs.at(-1) !== dialog) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        closeRef.current();
      }
      if (event.key === 'Tab') {
        const els = Array.from(
          ref.current?.querySelectorAll<HTMLElement>(
            'button:not([disabled]), a[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]',
          ) ?? [],
        ).filter((el) => el.tabIndex >= 0 && el.getClientRects().length > 0);
        if (!els?.length) return;
        const first = els[0],
          last = els[els.length - 1];
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === ref.current)
        ) {
          event.preventDefault();
          last.focus();
        } else if (
          !event.shiftKey &&
          (document.activeElement === last || document.activeElement === ref.current)
        ) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    const containFocus = (event: FocusEvent) => {
      if (
        openDialogs.at(-1) === dialog &&
        event.target instanceof Node &&
        !dialog?.contains(event.target)
      ) {
        dialog?.focus({ preventScroll: true });
      }
    };
    document.addEventListener('keydown', handler);
    document.addEventListener('focusin', containFocus);
    return () => {
      if (dialog) {
        const position = openDialogs.indexOf(dialog);
        if (position !== -1) openDialogs.splice(position, 1);
      }
      document.body.style.overflow = previousOverflow;
      if (root) root.inert = rootWasInert;
      document.removeEventListener('keydown', handler);
      document.removeEventListener('focusin', containFocus);
      previous?.focus();
    };
  }, []);
  return createPortal(
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && openDialogs.at(-1) === ref.current) onClose();
      }}
    >
      <div
        className={'modal ' + (wide ? 'wide' : '')}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={ref}
      >
        <div className="modal-heading">
          <span className="modal-symbol" aria-hidden="true">
            <PanelsTopLeft size={20} />
          </span>
          <div className="modal-title-block">
            <span className="modal-kicker">DERMA LIBRARY</span>
            <h2 id={titleId}>{title}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Đóng">
            <X />
          </button>
        </div>
        <div className="modal-content">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
