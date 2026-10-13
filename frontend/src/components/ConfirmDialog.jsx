import { useEffect, useRef } from 'react';

/**
 * Modal confirmation. Focus moves to the safe (cancel) button, Tab stays inside,
 * Escape cancels, and focus returns to whatever opened it.
 */
export default function ConfirmDialog({ title, children, confirmLabel, pending, onConfirm, onCancel }) {
  const cancelRef = useRef(null);
  const confirmRef = useRef(null);

  useEffect(() => {
    const opener = document.activeElement;
    cancelRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  function onKeyDown(event) {
    if (event.key === 'Escape') onCancel();
    if (event.key === 'Tab') {
      const first = cancelRef.current;
      const last = confirmRef.current;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  return (
    <div className="dialog-backdrop">
      <div role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="dialog" onKeyDown={onKeyDown}>
        <h2 id="dialog-title">{title}</h2>
        <p>{children}</p>
        <div className="dialog-actions">
          <button type="button" ref={cancelRef} className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" ref={confirmRef} className="btn btn-danger" disabled={pending} onClick={onConfirm}>
            {pending ? 'Deleting…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
