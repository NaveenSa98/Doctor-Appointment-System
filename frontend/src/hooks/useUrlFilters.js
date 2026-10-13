import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

export const STATUSES = ['scheduled', 'confirmed', 'completed', 'cancelled', 'no_show'];
export const SORTS = [
  'start_time',
  '-start_time',
  'patient_name',
  '-patient_name',
  'created_at',
  '-created_at',
];
export const DEFAULT_SORT = 'start_time';

/** Read filters from the query string, ignoring values the API would reject. */
function parse(params) {
  const sort = params.get('sort');
  const page = parseInt(params.get('page') ?? '1', 10);
  return {
    q: (params.get('q') ?? '').slice(0, 100),
    status: params.getAll('status').filter((s) => STATUSES.includes(s)),
    doctor_id: params.get('doctor_id') ?? '',
    hospital_id: params.get('hospital_id') ?? '',
    sort: SORTS.includes(sort) ? sort : DEFAULT_SORT,
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

/** Write filters to the query string, omitting defaults to keep URLs short. */
function serialize(f) {
  const p = new URLSearchParams();
  if (f.q) p.set('q', f.q);
  f.status.forEach((s) => p.append('status', s));
  if (f.doctor_id) p.set('doctor_id', f.doctor_id);
  if (f.hospital_id) p.set('hospital_id', f.hospital_id);
  if (f.sort !== DEFAULT_SORT) p.set('sort', f.sort);
  if (f.page > 1) p.set('page', String(f.page));
  return p;
}

/**
 * Appointment list filters kept in the URL, so they survive a reload and can be shared.
 * Changing any filter resets to page 1; pass `page` in the patch to change the page.
 */
export function useUrlFilters() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => parse(params), [params]);

  const setFilters = useCallback(
    (patch) =>
      setParams((prev) => serialize({ ...parse(prev), page: 1, ...patch }), {
        replace: 'q' in patch,
      }),
    [setParams],
  );

  const clearFilters = useCallback(() => setParams(new URLSearchParams()), [setParams]);

  const hasActiveFilters = Boolean(
    filters.q || filters.status.length || filters.doctor_id || filters.hospital_id,
  );

  return { filters, setFilters, clearFilters, hasActiveFilters };
}
