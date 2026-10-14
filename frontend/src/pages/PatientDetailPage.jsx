import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getPatient } from '../api/patients';
import BookingCard from '../components/BookingCard';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { formatDateTime } from '../utils/datetime';

function registeredOn(iso) {
  return new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
}

/** One patient's details and bookings (a doctor sees only the bookings with themself). */
export default function PatientDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data, error, isPending, isError, refetch } = useQuery({
    queryKey: ['patients', id],
    queryFn: () => getPatient(id),
  });

  if (isPending) return <Spinner label="Loading patient" />;
  if (isError) {
    return (
      <div className="container narrow">
        <ErrorState error={error} onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="container narrow">
      <div className="page-head">
        <h1 className="page-title">{data.full_name ?? data.email}</h1>
        <Link to="/patients" className="btn btn-secondary">
          All patients
        </Link>
      </div>

      <section className="card settings-card" aria-label="Patient details">
        <dl className="summary">
          <div>
            <dt>Email</dt>
            <dd>{data.email}</dd>
          </div>
          <div>
            <dt>Registered</dt>
            <dd>{registeredOn(data.created_at)}</dd>
          </div>
          <div>
            <dt>{user?.role === 'doctor' ? 'Bookings with you' : 'Bookings'}</dt>
            <dd>{data.booking_count}</dd>
          </div>
          <div>
            <dt>Latest booking</dt>
            <dd>{data.last_booking_at ? formatDateTime(data.last_booking_at) : '–'}</dd>
          </div>
        </dl>
      </section>

      <h2 className="section-title">Bookings</h2>
      {data.bookings.length === 0 ? (
        <EmptyState title="No bookings yet" />
      ) : (
        <ul className="bookings">
          {data.bookings.map((a) => (
            <BookingCard key={a.id} appointment={a} to={`/appointments/${a.id}`} />
          ))}
        </ul>
      )}
    </div>
  );
}
