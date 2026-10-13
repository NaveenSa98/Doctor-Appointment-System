import { Link, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listAppointments } from '../api/appointments';
import DayView from '../components/DayView';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { useDoctors } from '../hooks/useDoctors';
import { localDayRange, shiftDate } from '../utils/datetime';
import { todayLocal } from '../utils/slots';

const DAY_LIMIT = 100;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Agenda for one local day, grouped by doctor. The date and doctor live in the URL. */
export default function DayViewPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const date = DATE_RE.test(params.get('date') ?? '') ? params.get('date') : todayLocal();
  const doctorId = params.get('doctor_id') ?? '';
  const doctors = useDoctors();

  const { data, error, isPending, isError, refetch } = useQuery({
    queryKey: ['appointments', 'day', date, doctorId],
    queryFn: () => {
      const { from, to } = localDayRange(date);
      return listAppointments({
        date_from: from,
        date_to: to,
        doctor_id: doctorId,
        sort: 'start_time',
        page_size: DAY_LIMIT,
      });
    },
    placeholderData: keepPreviousData,
  });

  const update = (patch) =>
    setParams({ date, ...(doctorId && { doctor_id: doctorId }), ...patch }, { replace: true });

  let body;
  if (isPending) body = <Spinner label="Loading the day" />;
  else if (isError && !data) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.items.length === 0) {
    body = <EmptyState title="Nothing booked for this day" />;
  } else {
    body = (
      <>
        <DayView items={data.items} />
        {data.total > DAY_LIMIT && (
          <p className="muted">
            Showing the first {DAY_LIMIT} of {data.total} appointments.
          </p>
        )}
      </>
    );
  }

  return (
    <div className="container">
      <div className="page-head">
        <h1 className="page-title">Day view</h1>
        <Link to="/appointments" className="btn btn-secondary">
          Back to list
        </Link>
      </div>
      <div className="day-controls">
        <button type="button" className="btn btn-secondary" onClick={() => update({ date: shiftDate(date, -1) })}>
          Previous day
        </button>
        <div className="field">
          <label htmlFor="day">Date</label>
          <input id="day" type="date" value={date} onChange={(e) => e.target.value && update({ date: e.target.value })} />
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => update({ date: shiftDate(date, 1) })}>
          Next day
        </button>
        {user?.role !== 'doctor' && (
          <div className="field">
            <label htmlFor="day-doctor">Doctor</label>
            <select id="day-doctor" value={doctorId} onChange={(e) => update({ doctor_id: e.target.value })}>
              <option value="">All doctors</option>
              {(doctors.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      {body}
    </div>
  );
}
