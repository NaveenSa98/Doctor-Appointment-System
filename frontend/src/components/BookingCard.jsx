import { Link } from 'react-router-dom';
import { formatDateTime } from '../utils/datetime';
import { TYPES } from './AppointmentForm';
import StatusBadge from './StatusBadge';

/** One booking as a card. With `to`, the date links to the staff edit page. */
export default function BookingCard({ appointment: a, to }) {
  const when = formatDateTime(a.start_time);
  return (
    <li className="booking">
      <div>
        <strong>{to ? <Link to={to}>{when}</Link> : when}</strong>
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
