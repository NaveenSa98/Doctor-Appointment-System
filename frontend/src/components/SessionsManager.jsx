import { useState } from 'react';
import {
  useCreateSession,
  useDeleteSession,
  useRestoreDate,
  useSchedule,
  useSkipDate,
} from '../hooks/useSchedule';
import { errorMessage } from '../utils/errors';
import { HALF_HOURS, WEEKDAYS, formatDay, formatOffset } from '../utils/schedule';
import ConfirmDialog from './ConfirmDialog';
import Spinner from './Spinner';
import WeeklySchedule from './WeeklySchedule';

/** The friendlier message for the schedule's 409s, else the server's own. */
function scheduleError(err) {
  if (err?.code === 'session_overlap') return 'This doctor already has a session at that time on that day.';
  if (err?.code === 'session_has_appointments') {
    return 'There are upcoming appointments in this session. Cancel or move them first.';
  }
  if (err?.code === 'already_skipped') return 'That day is already skipped.';
  return errorMessage(err);
}

function AddSessionForm({ doctor, onAdded }) {
  const create = useCreateSession(doctor.id);
  const [hospitalId, setHospitalId] = useState(doctor.hospitals[0]?.id ?? '');
  const [weekday, setWeekday] = useState('0');
  const [start, setStart] = useState('09:00');
  const [end, setEnd] = useState('12:00');
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    if (end <= start) {
      setError('The session must end after it starts.');
      return;
    }
    try {
      await create.mutateAsync({ hospital_id: hospitalId, weekday: Number(weekday), start_time: start, end_time: end });
      setError(null);
      onAdded();
    } catch (err) {
      setError(scheduleError(err));
    }
  }

  return (
    <form className="add-session" onSubmit={submit} noValidate>
      <h3>Add a weekly session</h3>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="session-hospital">Hospital</label>
          <select id="session-hospital" value={hospitalId} onChange={(e) => setHospitalId(e.target.value)}>
            {doctor.hospitals.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="session-day">Day</label>
          <select id="session-day" value={weekday} onChange={(e) => setWeekday(e.target.value)}>
            {WEEKDAYS.map((name, i) => (
              <option key={name} value={i}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="session-start">From</label>
          <select id="session-start" value={start} onChange={(e) => setStart(e.target.value)}>
            {HALF_HOURS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="session-end">To</label>
          <select id="session-end" value={end} onChange={(e) => setEnd(e.target.value)}>
            {HALF_HOURS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="btn btn-primary" disabled={create.isPending}>
        Add session
      </button>
    </form>
  );
}

function SkipForm({ session, onDone }) {
  const skip = useSkipDate();
  const [day, setDay] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState(null);

  async function submit(event) {
    event.preventDefault();
    if (!day) {
      setError('Choose the date to skip.');
      return;
    }
    try {
      await skip.mutateAsync({ id: session.id, date: day, reason: reason.trim() || null });
      onDone();
    } catch (err) {
      setError(scheduleError(err));
    }
  }

  return (
    <form className="skip-form" onSubmit={submit} noValidate>
      <div className="field">
        <label htmlFor={`skip-date-${session.id}`}>Date to skip</label>
        <input id={`skip-date-${session.id}`} type="date" value={day} onChange={(e) => setDay(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor={`skip-reason-${session.id}`}>Reason (optional)</label>
        <input id={`skip-reason-${session.id}`} value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />
      </div>
      <button type="submit" className="btn btn-primary" disabled={skip.isPending}>
        Skip this date
      </button>
      <button type="button" className="btn btn-secondary" onClick={onDone}>
        Cancel
      </button>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

/** Admin: a doctor's weekly sessions, with add, remove, and skip-a-date. */
export default function SessionsManager({ doctor }) {
  const { data, isPending, isError, error } = useSchedule(doctor.id);
  const remove = useDeleteSession();
  const restore = useRestoreDate();
  const [skipping, setSkipping] = useState(null);
  const [removing, setRemoving] = useState(null);
  const [message, setMessage] = useState(null);

  if (isPending) return <Spinner label="Loading sessions" />;
  if (isError) return <p className="field-error" role="alert">{errorMessage(error)}</p>;

  async function confirmRemove() {
    try {
      await remove.mutateAsync(removing.id);
      setMessage(null);
    } catch (err) {
      setMessage(scheduleError(err));
    }
    setRemoving(null);
  }

  async function restoreDay(session, item) {
    try {
      await restore.mutateAsync({ id: session.id, day: item.on_date });
      setMessage(null);
    } catch (err) {
      setMessage(scheduleError(err));
    }
  }

  const actions = {
    row: (s) => (
      <div className="session-actions">
        <button type="button" className="btn btn-secondary" onClick={() => setSkipping(skipping === s.id ? null : s.id)}>
          Skip a date
        </button>
        <button type="button" className="btn btn-danger-outline" onClick={() => setRemoving(s)}>
          Remove
        </button>
        {skipping === s.id && <SkipForm session={s} onDone={() => setSkipping(null)} />}
      </div>
    ),
    restore: (s, item) => (
      <button type="button" className="link-btn" onClick={() => restoreDay(s, item)} aria-label={`Restore ${formatDay(item.on_date)}`}>
        Restore
      </button>
    ),
  };

  return (
    <section className="card settings-card" aria-labelledby="sessions-title">
      <h2 id="sessions-title">Weekly sessions</h2>
      <p className="muted">Times are clinic time ({formatOffset(data.utc_offset_minutes)}).</p>
      {data.sessions.length === 0 ? (
        <p className="callout">
          No sessions yet, so this doctor can be booked at any time from 09:00 to 16:30. Adding a session
          switches them to the schedule you set here.
        </p>
      ) : (
        <WeeklySchedule sessions={data.sessions} actions={actions} />
      )}
      {message && (
        <p className="field-error" role="alert">
          {message}
        </p>
      )}
      <AddSessionForm doctor={doctor} onAdded={() => setMessage(null)} />
      {removing && (
        <ConfirmDialog
          title="Remove this session?"
          confirmLabel="Remove session"
          pending={remove.isPending}
          onConfirm={confirmRemove}
          onCancel={() => setRemoving(null)}
        >
          {WEEKDAYS[removing.weekday]} {removing.start_time}–{removing.end_time} at {removing.hospital.name} will no
          longer be bookable.
        </ConfirmDialog>
      )}
    </section>
  );
}
