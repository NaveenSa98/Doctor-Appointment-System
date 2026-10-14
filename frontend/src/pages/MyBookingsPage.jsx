import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listAppointments } from '../api/appointments';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import StatusBadge from '../components/StatusBadge';
import { TYPES } from '../components/AppointmentForm';
import { formatDateTime } from '../utils/datetime';

const INACTIVE = ['cancelled', 'completed', 'no_show'];

/** Split bookings into upcoming (still active, not yet started) and past, soonest first. */
export function splitBookings(items, now = Date.now()) {
  const upcoming = items
    .filter((a) => Date.parse(a.start_time) > now && !INACTIVE.includes(a.status))
    .sort((a, b) => Date.parse(a.start_time) - Date.parse(b.start_time));
  const past = items
    .filter((a) => !upcoming.includes(a))
    .sort((a, b) => Date.parse(b.start_time) - Date.parse(a.start_time));
  return { upcoming, past };
}

function BookingCard({ appointment: a }) {
  return (
    <li className="booking">
      <div>
        <strong>{formatDateTime(a.start_time)}</strong>
        <span className="sub">
          {a.doctor.full_name}, {a.doctor.specialty}
        </span>
        <span className="sub">
          {a.hospital.name} · {TYPES[a.appointment_type] ?? a.appointment_type} · for {a.patient_name}
        </span>
      </div>
      <StatusBadge status={a.status} />
    </li>
  );
}

function Section({ title, items }) {
  if (items.length === 0) return null;
  return (
    <section aria-label={title}>
      <h2 className="section-title">{title}</h2>
      <ul className="bookings">
        {items.map((a) => (
          <BookingCard key={a.id} appointment={a} />
        ))}
      </ul>
    </section>
  );
}

/** A patient's own bookings, upcoming first. */
export default function MyBookingsPage() {
  const { data, error, isPending, isError, refetch } = useQuery({
    queryKey: ['appointments', 'mine'],
    queryFn: () => listAppointments({ sort: '-start_time', page_size: 100 }),
  });

  let body;
  if (isPending) body = <Spinner label="Loading your bookings" />;
  else if (isError) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.items.length === 0) {
    body = (
      <EmptyState title="No bookings yet">
        <Link to="/book" className="btn btn-primary">
          Book an appointment
        </Link>
      </EmptyState>
    );
  } else {
    const { upcoming, past } = splitBookings(data.items);
    body = (
      <>
        <Section title="Upcoming" items={upcoming} />
        <Section title="Past and cancelled" items={past} />
        <p className="muted">To change or cancel a booking, please contact the clinic.</p>
      </>
    );
  }

  return (
    <div className="container narrow">
      <div className="page-head">
        <h1 className="page-title">My bookings</h1>
        <Link to="/book" className="btn btn-primary">
          New booking
        </Link>
      </div>
      {body}
    </div>
  );
}
