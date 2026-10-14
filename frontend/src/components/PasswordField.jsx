import { useState } from 'react';

/** Labelled password input with a Show/Hide toggle and an optional error or hint. */
export default function PasswordField({ id, label, value, onChange, autoComplete, error, hint, invalid }) {
  const [shown, setShown] = useState(false);
  const note = error ?? hint;
  const noteId = note ? `${id}-note` : undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        <input
          id={id}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error || invalid ? 'true' : undefined}
          aria-describedby={noteId}
          required
        />
        <button
          type="button"
          className="input-toggle"
          aria-pressed={shown}
          aria-label={shown ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          onClick={() => setShown((v) => !v)}
        >
          {shown ? 'Hide' : 'Show'}
        </button>
      </div>
      {note && (
        <p id={noteId} className={error ? 'field-error' : 'field-hint'}>
          {note}
        </p>
      )}
    </div>
  );
}
