import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ConfirmDialog from '../components/ConfirmDialog';
import ErrorState from '../components/ErrorState';
import PasswordField from '../components/PasswordField';
import SessionsManager from '../components/SessionsManager';
import Spinner from '../components/Spinner';
import {
  useAdminDoctor,
  useCreateDoctor,
  useDeleteDoctor,
  useSetDoctorAccount,
  useUpdateDoctor,
} from '../hooks/useAdminDoctors';
import { useHospitals } from '../hooks/useDoctors';
import { errorMessage, fieldErrors } from '../utils/errors';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** Turn a failed request into `{ field: message }`, with `form` for anything not tied to a field. */
function toErrors(err) {
  if (err?.status === 409 && err.code === 'email_taken') return { email: 'Another account already uses this email.' };
  const byField = fieldErrors(err);
  const mapped = {
    full_name: byField.full_name,
    specialty: byField.specialty,
    hospital_ids: byField.hospital_ids,
    email: byField.email ?? byField['account.email'],
    password: byField.password ?? byField['account.password'],
  };
  const hasField = Object.values(mapped).some(Boolean);
  return hasField ? mapped : { form: errorMessage(err) };
}

function Message({ error, saved }) {
  if (error) {
    return (
      <p className="field-error" role="alert">
        {error}
      </p>
    );
  }
  return saved ? <p className="field-ok" role="status">{saved}</p> : null;
}

function FieldNote({ id, error }) {
  return error ? (
    <p id={id} className="field-error">
      {error}
    </p>
  ) : null;
}

/** Name, specialty and hospitals, plus (when creating) an optional login. */
function ProfileForm({ doctor, hospitals, onSubmit, submitLabel }) {
  const creating = !doctor;
  const [name, setName] = useState(doctor?.full_name ?? '');
  const [specialty, setSpecialty] = useState(doctor?.specialty ?? '');
  const [selected, setSelected] = useState(() => new Set(doctor?.hospitals.map((h) => h.id)));
  const [withLogin, setWithLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState('');
  const [pending, setPending] = useState(false);

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function validate() {
    const found = {};
    if (name.trim().length < 2) found.full_name = 'Enter the doctor’s full name.';
    if (specialty.trim().length < 2) found.specialty = 'Enter a specialty.';
    if (selected.size === 0) found.hospital_ids = 'Choose at least one hospital.';
    if (creating && withLogin) {
      if (!EMAIL_RE.test(email.trim())) found.email = 'Enter a valid email address.';
      if (password.length < 8) found.password = 'Use at least 8 characters.';
    }
    return found;
  }

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const found = validate();
    setErrors(found);
    setSaved('');
    if (Object.keys(found).length > 0) return;

    const body = { full_name: name.trim(), specialty: specialty.trim(), hospital_ids: [...selected] };
    if (creating && withLogin) body.account = { email: email.trim(), password };
    setPending(true);
    try {
      await onSubmit(body);
      if (!creating) setSaved('Saved.');
    } catch (err) {
      setErrors(toErrors(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card form-card" onSubmit={submit} noValidate>
      {errors.form && (
        <div className="alert" role="alert">
          {errors.form}
        </div>
      )}
      <div className="form-grid">
        <div className="field">
          <label htmlFor="full_name">Full name</label>
          <input id="full_name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={errors.full_name ? 'true' : undefined} aria-describedby={errors.full_name ? 'full_name-note' : undefined} />
          <FieldNote id="full_name-note" error={errors.full_name} />
        </div>
        <div className="field">
          <label htmlFor="specialty">Specialty</label>
          <input id="specialty" value={specialty} onChange={(e) => setSpecialty(e.target.value)} aria-invalid={errors.specialty ? 'true' : undefined} aria-describedby={errors.specialty ? 'specialty-note' : undefined} />
          <FieldNote id="specialty-note" error={errors.specialty} />
        </div>
      </div>

      <fieldset className="chips hospital-picks" aria-describedby={errors.hospital_ids ? 'hospital_ids-note' : undefined}>
        <legend>Hospitals</legend>
        {hospitals.map((h) => (
          <label key={h.id} className={selected.has(h.id) ? 'chip chip-on' : 'chip'}>
            <input type="checkbox" checked={selected.has(h.id)} onChange={() => toggle(h.id)} />
            {h.name}
          </label>
        ))}
      </fieldset>
      <FieldNote id="hospital_ids-note" error={errors.hospital_ids} />

      {creating && (
        <section className="login-box" aria-label="Login">
          <label className="check">
            <input type="checkbox" checked={withLogin} onChange={(e) => setWithLogin(e.target.checked)} />
            Create a login for this doctor now
          </label>
          {withLogin && (
            <div className="form-grid">
              <div className="field">
                <label htmlFor="login-email">Login email</label>
                <input id="login-email" type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={errors.email ? 'true' : undefined} aria-describedby={errors.email ? 'login-email-note' : undefined} />
                <FieldNote id="login-email-note" error={errors.email} />
              </div>
              <PasswordField id="login-password" label="Initial password" autoComplete="new-password" value={password} onChange={setPassword} error={errors.password} hint="Share it with the doctor securely." />
            </div>
          )}
        </section>
      )}

      <Message saved={saved} />
      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-lg" disabled={pending}>
          {pending ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}

function LoginSection({ doctor }) {
  const set = useSetDoctorAccount(doctor.id);
  const [email, setEmail] = useState(doctor.account?.email ?? '');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState('');
  const has = Boolean(doctor.account);

  async function submit(event) {
    event.preventDefault();
    setSaved('');
    const body = {};
    if (!has || email.trim() !== doctor.account.email) body.email = email.trim();
    if (password) body.password = password;
    if (Object.keys(body).length === 0) {
      setErrors({ form: 'Change the email or enter a new password first.' });
      return;
    }
    if (!has && (!body.email || !body.password)) {
      setErrors({ form: 'Enter both an email and a password to create the login.' });
      return;
    }
    try {
      await set.mutateAsync(body);
      setErrors({});
      setPassword('');
      setSaved(has ? 'Login updated.' : 'Login created.');
    } catch (err) {
      setErrors(toErrors(err));
    }
  }

  return (
    <form className="card settings-card" onSubmit={submit} noValidate>
      <h2>Login</h2>
      <p className="muted">
        {has ? 'The doctor signs in with this email. Enter a new password to reset it.' : 'This doctor has no login yet.'}
      </p>
      <div className="field">
        <label htmlFor="acct-email">Login email</label>
        <input id="acct-email" type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={errors.email ? 'true' : undefined} />
        <FieldNote id="acct-email-note" error={errors.email} />
      </div>
      <PasswordField id="acct-password" label={has ? 'New password' : 'Initial password'} autoComplete="new-password" value={password} onChange={setPassword} error={errors.password} hint="At least 8 characters." />
      <Message error={errors.form} saved={saved} />
      <button type="submit" className="btn btn-primary" disabled={set.isPending}>
        {has ? 'Update login' : 'Create login'}
      </button>
    </form>
  );
}

function StatusSection({ doctor }) {
  const update = useUpdateDoctor(doctor.id);
  const [error, setError] = useState(null);

  async function toggle() {
    setError(null);
    try {
      await update.mutateAsync({ is_active: !doctor.is_active });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="card settings-card" aria-labelledby="status-title">
      <h2 id="status-title">Availability</h2>
      <p className="muted">
        {doctor.is_active
          ? 'This doctor can be booked and can sign in. Deactivating hides them from the booking form and blocks their login; existing bookings stay.'
          : 'This doctor is hidden from the booking form and cannot sign in.'}
      </p>
      <Message error={error} />
      <button type="button" className="btn btn-secondary" onClick={toggle} disabled={update.isPending}>
        {doctor.is_active ? 'Deactivate doctor' : 'Reactivate doctor'}
      </button>
    </section>
  );
}

function DeleteSection({ doctor }) {
  const remove = useDeleteDoctor(doctor.id);
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState(null);

  async function onConfirm() {
    try {
      await remove.mutateAsync();
      navigate('/admin/doctors', { replace: true });
    } catch (err) {
      setError(
        err?.code === 'doctor_has_appointments'
          ? 'This doctor has appointments, so they cannot be deleted. Deactivate them instead.'
          : errorMessage(err),
      );
      setOpen(false);
    }
  }

  return (
    <section className="card settings-card danger-zone" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete doctor</h2>
      <p className="muted">
        Permanently removes the doctor and their login. This is only possible while they have no appointments.
      </p>
      <Message error={error} />
      <button type="button" className="btn btn-danger-outline" onClick={() => setOpen(true)}>
        Delete doctor
      </button>
      {open && (
        <ConfirmDialog
          title={`Delete ${doctor.full_name}?`}
          confirmLabel="Delete doctor"
          pending={remove.isPending}
          onConfirm={onConfirm}
          onCancel={() => setOpen(false)}
        >
          This cannot be undone.
        </ConfirmDialog>
      )}
    </section>
  );
}

/** `/admin/doctors/new` creates a doctor; `/admin/doctors/:id` edits one. */
export default function AdminDoctorFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const hospitals = useHospitals();
  const doctor = useAdminDoctor(id);
  const create = useCreateDoctor();
  const update = useUpdateDoctor(id);

  if (hospitals.isPending || (id && doctor.isPending)) return <Spinner label="Loading" />;
  const failed = hospitals.error ?? (id ? doctor.error : null);
  if (failed) {
    return (
      <div className="container narrow">
        <ErrorState error={failed} onRetry={() => { hospitals.refetch(); doctor.refetch(); }} />
      </div>
    );
  }

  if (!id) {
    return (
      <div className="container narrow">
        <h1 className="page-title">Add a doctor</h1>
        <ProfileForm
          hospitals={hospitals.data}
          submitLabel="Add doctor"
          onSubmit={async (body) => {
            const created = await create.mutateAsync(body);
            navigate(`/admin/doctors/${created.id}`, { replace: true });
          }}
        />
      </div>
    );
  }

  return (
    <div className="container narrow">
      <div className="page-head">
        <h1 className="page-title">{doctor.data.full_name}</h1>
        <button type="button" className="btn btn-secondary" onClick={() => navigate('/admin/doctors')}>
          Back to doctors
        </button>
      </div>
      <div className="settings">
        <ProfileForm
          key={doctor.data.id}
          doctor={doctor.data}
          hospitals={hospitals.data}
          submitLabel="Save changes"
          onSubmit={(body) => update.mutateAsync(body)}
        />
        <LoginSection key={`login-${doctor.data.account?.email ?? 'none'}`} doctor={doctor.data} />
        <SessionsManager doctor={doctor.data} />
        <StatusSection doctor={doctor.data} />
        <DeleteSection doctor={doctor.data} />
      </div>
    </div>
  );
}
