import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import WeeklySchedule from '../components/WeeklySchedule';
import { useAuth } from '../hooks/AuthContext';
import { useSchedule } from '../hooks/useSchedule';
import { formatOffset } from '../utils/schedule';

/** A doctor's own weekly sessions (read-only: the admin sets them). */
export default function MySchedulePage() {
  const { user } = useAuth();
  const { data, error, isPending, isError, refetch } = useSchedule(user.doctor_id);

  let body;
  if (isPending) body = <Spinner label="Loading your schedule" />;
  else if (isError) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.sessions.length === 0) {
    body = (
      <EmptyState title="No sessions set yet">
        Until an administrator sets your weekly sessions you can be booked from 09:00 to 16:30. Ask them if you
        need set hours.
      </EmptyState>
    );
  } else {
    body = (
      <section className="card settings-card">
        <p className="muted">Times are clinic time ({formatOffset(data.utc_offset_minutes)}).</p>
        <WeeklySchedule sessions={data.sessions} />
        <p className="muted">To change your sessions, please contact an administrator.</p>
      </section>
    );
  }

  return (
    <div className="container narrow">
      <div className="page-head">
        <h1 className="page-title">My schedule</h1>
        <Link to="/appointments" className="btn btn-secondary">
          My appointments
        </Link>
      </div>
      {body}
    </div>
  );
}
