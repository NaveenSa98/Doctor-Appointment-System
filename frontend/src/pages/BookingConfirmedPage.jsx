import { Link, Navigate, useLocation } from 'react-router-dom';
import { formatDateTime } from '../utils/datetime';

/** Shows the reference id. Opened directly (no booking in state) it sends the visitor to /book. */
export default function BookingConfirmedPage() {
  const appointment = useLocation().state?.appointment;
  if (!appointment) return <Navigate to="/book" replace />;

  return (
    <div className="container narrow">
      <div className="card confirmed">
        <span className="confirmed-mark" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12l5 5 9-10" />
          </svg>
        </span>
        <h1 className="page-title">You are booked</h1>
        <p className="muted">Keep this reference number. Staff will ask for it if you need to change your visit.</p>
        <p className="reference" aria-label="Reference number">
          {appointment.id}
        </p>
        <dl className="summary">
          <div>
            <dt>Patient</dt>
            <dd>{appointment.patient_name}</dd>
          </div>
          <div>
            <dt>Doctor</dt>
            <dd>
              {appointment.doctor.full_name}, {appointment.doctor.specialty}
            </dd>
          </div>
          <div>
            <dt>Hospital</dt>
            <dd>{appointment.hospital.name}</dd>
          </div>
          <div>
            <dt>When</dt>
            <dd>{formatDateTime(appointment.start_time)}</dd>
          </div>
        </dl>
        <Link to="/book" className="btn btn-secondary">
          Book another
        </Link>
      </div>
    </div>
  );
}
