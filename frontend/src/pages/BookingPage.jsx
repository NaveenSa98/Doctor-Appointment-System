import { useNavigate } from 'react-router-dom';
import AppointmentForm from '../components/AppointmentForm';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { useCreateAppointment } from '../hooks/useAppointmentMutations';
import { toCreatePayload } from '../utils/appointmentPayload';

/** Public booking: works without signing in. A signed-in doctor is pre-selected. */
export default function BookingPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const create = useCreateAppointment();

  // The form reads its default values once, so wait until we know who is signed in.
  if (loading) return <Spinner label="Loading" />;

  async function onSubmit(values) {
    const appointment = await create.mutateAsync(toCreatePayload(values, { includeStatus: false }));
    navigate('/book/confirmed', { state: { appointment } });
  }

  return (
    <div className="container narrow">
      <h1 className="page-title">Book an appointment</h1>
      <AppointmentForm user={user} submitLabel="Book appointment" onSubmit={onSubmit} />
    </div>
  );
}
