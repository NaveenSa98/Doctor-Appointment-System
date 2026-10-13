import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAppointment } from '../api/appointments';
import AppointmentForm from '../components/AppointmentForm';
import ConfirmDialog from '../components/ConfirmDialog';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import {
  useCreateAppointment,
  useDeleteAppointment,
  useUpdateAppointment,
} from '../hooks/useAppointmentMutations';
import { toCreatePayload, toPatchPayload } from '../utils/appointmentPayload';

/** Staff page: create (`/appointments/new`) or edit and delete (`/appointments/:id`). */
export default function AppointmentFormPage() {
  const { id } = useParams();
  return id ? <EditAppointment id={id} /> : <NewAppointment />;
}

function NewAppointment() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const create = useCreateAppointment();

  async function onSubmit(values) {
    await create.mutateAsync(toCreatePayload(values, { includeStatus: true }));
    navigate('/appointments');
  }

  return (
    <div className="container narrow">
      <h1 className="page-title">New appointment</h1>
      <AppointmentForm
        user={user}
        showStatus
        submitLabel="Create appointment"
        onSubmit={onSubmit}
        onCancel={() => navigate('/appointments')}
      />
    </div>
  );
}

function EditAppointment({ id }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const query = useQuery({ queryKey: ['appointment', id], queryFn: () => getAppointment(id) });
  const update = useUpdateAppointment(id);
  const remove = useDeleteAppointment(id);

  if (query.isPending) return <Spinner label="Loading appointment" />;
  if (query.isError) {
    return (
      <div className="container narrow">
        <ErrorState error={query.error} onRetry={query.refetch} />
      </div>
    );
  }

  async function onSubmit(values) {
    const patch = toPatchPayload(values, query.data);
    if (Object.keys(patch).length > 0) await update.mutateAsync(patch);
    navigate('/appointments');
  }

  async function onDelete() {
    await remove.mutateAsync();
    navigate('/appointments');
  }

  return (
    <div className="container narrow">
      <div className="page-head">
        <h1 className="page-title">Edit appointment</h1>
        <button type="button" className="btn btn-danger-outline" onClick={() => setConfirming(true)}>
          Delete
        </button>
      </div>
      <AppointmentForm
        initial={query.data}
        user={user}
        showStatus
        submitLabel="Save changes"
        onSubmit={onSubmit}
        onCancel={() => navigate('/appointments')}
      />
      {confirming && (
        <ConfirmDialog
          title="Delete this appointment?"
          confirmLabel="Delete"
          pending={remove.isPending}
          onConfirm={onDelete}
          onCancel={() => setConfirming(false)}
        >
          This removes the appointment for {query.data.patient_name} and frees the time slot.
        </ConfirmDialog>
      )}
    </div>
  );
}
