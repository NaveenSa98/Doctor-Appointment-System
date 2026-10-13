import { useEffect, useState } from 'react';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { STATUSES } from '../hooks/useUrlFilters';
import { STATUS_LABELS } from './StatusBadge';

/** Search (debounced 300 ms), status checkboxes, doctor and hospital selects. */
export default function AppointmentFilters({ filters, onChange, doctors = [], hospitals = [], showDoctor = true }) {
  const [search, setSearch] = useState(filters.q);
  const debounced = useDebouncedValue(search, 300);

  // Push the debounced text to the URL.
  useEffect(() => {
    if (debounced.trim() !== filters.q) onChange({ q: debounced.trim() });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  // Follow external changes (clear filters, back button) without clobbering typing.
  useEffect(() => {
    if (filters.q !== debounced.trim()) setSearch(filters.q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.q]);

  function toggleStatus(status) {
    const next = filters.status.includes(status)
      ? filters.status.filter((s) => s !== status)
      : [...filters.status, status];
    onChange({ status: next });
  }

  return (
    <form role="search" className="filters" onSubmit={(e) => e.preventDefault()}>
      <div className="filters-row">
        <div className="search-field">
          <label htmlFor="q" className="sr-only">Search patient name</label>
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-4-4" />
          </svg>
          <input id="q" type="search" maxLength={100} placeholder="Search patient name" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {showDoctor && (
          <select aria-label="Doctor" value={filters.doctor_id} onChange={(e) => onChange({ doctor_id: e.target.value })}>
            <option value="">All doctors</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>{d.full_name}</option>
            ))}
          </select>
        )}
        <select aria-label="Hospital" value={filters.hospital_id} onChange={(e) => onChange({ hospital_id: e.target.value })}>
          <option value="">All hospitals</option>
          {hospitals.map((h) => (
            <option key={h.id} value={h.id}>{h.name}</option>
          ))}
        </select>
      </div>
      <fieldset className="chips">
        <legend>Status</legend>
        {STATUSES.map((s) => (
          <label key={s} className={filters.status.includes(s) ? 'chip chip-on' : 'chip'}>
            <input type="checkbox" checked={filters.status.includes(s)} onChange={() => toggleStatus(s)} />
            {STATUS_LABELS[s]}
          </label>
        ))}
      </fieldset>
    </form>
  );
}
