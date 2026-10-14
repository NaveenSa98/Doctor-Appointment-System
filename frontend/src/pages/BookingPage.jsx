import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppointmentForm from '../components/AppointmentForm';
import DoctorSearch from '../components/DoctorSearch';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { useCreateAppointment } from '../hooks/useAppointmentMutations';
import { toCreatePayload } from '../utils/appointmentPayload';

/** Public booking: works without signing in. A signed-in doctor is pre-selected. */
export default function BookingPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const create = useCreateAppointment();
  const [prefill, setPrefill] = useState(null);

  // The form reads its default values once, so wait until we know who is signed in.
  if (loading) return <Spinner label="Loading" />;

  async function onSubmit(values) {
    const appointment = await create.mutateAsync(toCreatePayload(values, { includeStatus: false }));
    navigate('/book/confirmed', { state: { appointment } });
  }

  function onChoose({ doctorId, hospitalId, date }) {
    // A new object each time, so choosing the same doctor again still refills the form.
    setPrefill({ doctor_id: doctorId, hospital_id: hospitalId, date });
    document.getElementById('booking-form')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className="container narrow wide-search">
      <h1 className="page-title">Book an appointment</h1>
      {user?.role !== 'doctor' && <DoctorSearch onChoose={onChoose} />}
      <div id="booking-form">
        <AppointmentForm user={user} prefill={prefill} submitLabel="Book appointment" onSubmit={onSubmit} />
      </div>
    </div>
  );
}
