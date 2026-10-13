import { slotLabel } from '../utils/slots';

/**
 * Grid of time buttons. Taken and past slots are disabled; the chosen one is `aria-pressed`.
 * @param {{ slots: string[], value: string, taken: Set<number>, onChange: (iso: string) => void }} props
 */
export default function SlotPicker({ slots, value, taken, onChange, loading, error, errorId, hint }) {
  const now = Date.now();
  return (
    <fieldset className="slots" aria-describedby={error ? errorId : undefined}>
      <legend>Time</legend>
      {hint ? (
        <p className="muted slots-hint">{hint}</p>
      ) : (
        <div className="slot-grid" aria-busy={loading}>
          {slots.map((iso) => {
            const ms = Date.parse(iso);
            const selected = value && Date.parse(value) === ms;
            const unavailable = taken.has(ms) || ms <= now;
            return (
              <button
                key={iso}
                type="button"
                className={selected ? 'slot slot-on' : 'slot'}
                aria-pressed={Boolean(selected)}
                disabled={unavailable && !selected}
                onClick={() => onChange(iso)}
              >
                {slotLabel(iso)}
                {unavailable && <span className="sr-only"> (unavailable)</span>}
              </button>
            );
          })}
        </div>
      )}
      {error && (
        <p id={errorId} className="field-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
