import { Controller, useForm } from 'react-hook-form';
import { useAvailability } from '../hooks/useAvailability';
import { useDoctors, useHospitals } from '../hooks/useDoctors';
import { STATUSES } from '../hooks/useUrlFilters';
import { errorMessage, fieldErrors } from '../utils/errors';
import { utcIsoToLocalInput } from '../utils/datetime';
import { slotsForDate, todayLocal } from '../utils/slots';
import ErrorState from './ErrorState';
import SlotPicker from './SlotPicker';
import Spinner from './Spinner';
import { STATUS_LABELS } from './StatusBadge';

export const TYPES = {
  consultation: 'Consultation',
  follow_up: 'Follow-up',
  check_up: 'Check-up',
  procedure: 'Procedure',
  vaccination: 'Vaccination',
};

const FORM_FIELDS = ['patient_name', 'doctor_id', 'hospital_id', 'start_time', 'appointment_type', 'status'];

function toFormValues(initial, lockedDoctorId) {
  if (initial) {
    return {
      hospital_id: initial.hospital.id,
      doctor_id: initial.doctor.id,
      date: utcIsoToLocalInput(initial.start_time).slice(0, 10),
      start_time: initial.start_time,
      appointment_type: initial.appointment_type,
      patient_name: initial.patient_name,
      status: initial.status,
    };
  }
  return {
    hospital_id: '',
    doctor_id: lockedDoctorId ?? '',
    date: '',
    start_time: '',
    appointment_type: 'consultation',
    patient_name: '',
    status: 'scheduled',
  };
}

/** Keep the appointment's current doctor/hospital in a list even if it is no longer offered. */
function withCurrent(list, current, extra) {
  const base = list ?? [];
  return current && !base.some((x) => x.id === current.id) ? [...base, { ...current, ...extra }] : base;
}

/** Show API errors on the field they belong to (a 409 lands on the time). */
function applyServerError(err, setError) {
  if (err?.status === 409) {
    setError('start_time', { message: 'That time is no longer available. Pick another slot.' });
    return;
  }
  const known = Object.entries(fieldErrors(err)).filter(([f]) => FORM_FIELDS.includes(f));
  known.forEach(([field, message]) => setError(field, { message }));
  if (known.length === 0) setError('root.server', { message: errorMessage(err) });
}

function FieldError({ id, message }) {
  return message ? (
    <p id={id} className="field-error">
      {message}
    </p>
  ) : null;
}

/**
 * Create/edit form shared by the public booking page and the staff pages.
 * `onSubmit(values)` should reject with the API error so it is shown on the right field.
 */
export default function AppointmentForm({ initial, user, showStatus, submitLabel, onSubmit, onCancel }) {
  const doctorsQuery = useDoctors();
  const hospitalsQuery = useHospitals();
  const lockedDoctorId = user?.role === 'doctor' ? user.doctor_id : null;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: toFormValues(initial, lockedDoctorId) });
  const [doctorId, hospitalId, date, startTime] = watch(['doctor_id', 'hospital_id', 'date', 'start_time']);

  const allDoctors = withCurrent(doctorsQuery.data, initial?.doctor, {
    hospitals: initial ? [initial.hospital] : [],
  });
  const doctor = allDoctors.find((d) => d.id === doctorId);
  const doctorOptions = allDoctors.filter(
    (d) =>
      (!lockedDoctorId || d.id === lockedDoctorId) &&
      (!hospitalId || d.hospitals.some((h) => h.id === hospitalId)),
  );
  const hospitalOptions = doctor
    ? withCurrent(doctor.hospitals, initial?.hospital)
    : withCurrent(hospitalsQuery.data, initial?.hospital);

  const availability = useAvailability(doctorId, date);
  const taken = new Set((availability.data?.taken ?? []).map((iso) => Date.parse(iso)));
  const slots = date ? slotsForDate(date) : [];
  const hasStart = startTime && slots.some((s) => Date.parse(s) === Date.parse(startTime));
  if (date && startTime && !hasStart && utcIsoToLocalInput(startTime).startsWith(date)) slots.push(startTime);
  const hint = !doctorId || !date ? 'Choose a doctor and a date to see times.' : null;

  function onDoctorChange(event) {
    const next = allDoctors.find((d) => d.id === event.target.value);
    if (next && !next.hospitals.some((h) => h.id === hospitalId)) {
      setValue('hospital_id', next.hospitals.length === 1 ? next.hospitals[0].id : '');
    }
    setValue('start_time', '');
  }

  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit(values);
    } catch (err) {
      applyServerError(err, setError);
    }
  });

  // Render the selects only once their options exist, so default values (e.g. a signed-in
  // doctor) are applied to a populated <select>.
  if (doctorsQuery.isPending || hospitalsQuery.isPending) return <Spinner label="Loading doctors" />;
  const loadError = doctorsQuery.error ?? hospitalsQuery.error;
  if (loadError) {
    return <ErrorState error={loadError} onRetry={() => { doctorsQuery.refetch(); hospitalsQuery.refetch(); }} />;
  }

  const invalid = (name) => (errors[name] ? 'true' : undefined);
  const describe = (name) => (errors[name] ? `${name}-error` : undefined);

  return (
    <form className="card form-card" onSubmit={submit} noValidate>
      {errors.root?.server && (
        <div className="alert" role="alert">
          {errors.root.server.message}
        </div>
      )}

      <div className="form-grid">
        <div className="field">
          <label htmlFor="hospital_id">Hospital</label>
          <select
            id="hospital_id"
            aria-invalid={invalid('hospital_id')}
            aria-describedby={describe('hospital_id')}
            {...register('hospital_id', { required: 'Choose a hospital.' })}
          >
            <option value="">Select a hospital</option>
            {hospitalOptions.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
          <FieldError id="hospital_id-error" message={errors.hospital_id?.message} />
        </div>

        <div className="field">
          <label htmlFor="doctor_id">Doctor</label>
          <select
            id="doctor_id"
            aria-invalid={invalid('doctor_id')}
            aria-describedby={describe('doctor_id')}
            {...register('doctor_id', { required: 'Choose a doctor.', onChange: onDoctorChange })}
          >
            <option value="">Select a doctor</option>
            {doctorOptions.map((d) => (
              <option key={d.id} value={d.id}>{`${d.full_name}, ${d.specialty}`}</option>
            ))}
          </select>
          <FieldError id="doctor_id-error" message={errors.doctor_id?.message} />
        </div>

        <div className="field">
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            min={initial ? undefined : todayLocal()}
            aria-invalid={invalid('date')}
            aria-describedby={describe('date')}
            {...register('date', { required: 'Choose a date.', onChange: () => setValue('start_time', '') })}
          />
          <FieldError id="date-error" message={errors.date?.message} />
        </div>

        <div className="field">
          <label htmlFor="appointment_type">Type</label>
          <select id="appointment_type" {...register('appointment_type', { required: true })}>
            {Object.entries(TYPES).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Controller
        name="start_time"
        control={control}
        rules={{ required: 'Choose a time.' }}
        render={({ field }) => (
          <SlotPicker
            slots={slots}
            value={field.value}
            taken={taken}
            loading={availability.isFetching}
            hint={hint}
            error={errors.start_time?.message}
            errorId="start_time-error"
            onChange={field.onChange}
          />
        )}
      />

      <div className="form-grid">
        <div className="field">
          <label htmlFor="patient_name">Patient name</label>
          <input
            id="patient_name"
            type="text"
            autoComplete="off"
            aria-invalid={invalid('patient_name')}
            aria-describedby={describe('patient_name')}
            {...register('patient_name', {
              validate: (v) => {
                const n = v.trim().length;
                if (n < 2) return 'Enter at least 2 characters.';
                if (n > 100) return 'Use 100 characters or fewer.';
                return true;
              },
            })}
          />
          <FieldError id="patient_name-error" message={errors.patient_name?.message} />
        </div>

        {showStatus && (
          <div className="field">
            <label htmlFor="status">Status</label>
            <select id="status" {...register('status')}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-lg" disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="btn btn-secondary btn-lg" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
