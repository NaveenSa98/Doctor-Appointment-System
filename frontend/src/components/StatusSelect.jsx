import { useState } from 'react';
import { STATUSES } from '../hooks/useUrlFilters';
import { useStatusChange } from '../hooks/useStatusChange';
import { errorMessage } from '../utils/errors';
import { STATUS_LABELS } from './StatusBadge';

/** Inline status dropdown for a table row. Updates at once and rolls back if the API refuses. */
export default function StatusSelect({ appointment }) {
  const change = useStatusChange();
  const [error, setError] = useState(null);

  function onChange(event) {
    setError(null);
    change.mutate(
      { id: appointment.id, status: event.target.value },
      { onError: (err) => setError(errorMessage(err)) },
    );
  }

  return (
    <div className="status-select-wrap">
      <select
        className={`status-select badge-${appointment.status}`}
        aria-label={`Status for ${appointment.patient_name}`}
        value={appointment.status}
        onChange={onChange}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABELS[s]}
          </option>
        ))}
      </select>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
