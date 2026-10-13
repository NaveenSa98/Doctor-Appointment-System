import { useStats } from '../hooks/useStats';
import { STATUSES } from '../hooks/useUrlFilters';
import { STATUS_LABELS } from './StatusBadge';

/** Count tiles: total plus one per status. Follows the list's doctor filter. */
export default function StatsTiles({ doctorId }) {
  const { data } = useStats(doctorId);
  const value = (n) => (data ? n : '–');

  return (
    <dl className="tiles" aria-label="Appointment counts">
      <div className="tile">
        <dt>Total</dt>
        <dd>{value(data?.total)}</dd>
      </div>
      {STATUSES.map((s) => (
        <div key={s} className="tile">
          <dt>{STATUS_LABELS[s]}</dt>
          <dd className={`tile-${s}`}>{value(data?.by_status?.[s])}</dd>
        </div>
      ))}
    </dl>
  );
}
