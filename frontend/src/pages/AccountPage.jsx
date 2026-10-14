import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteAccount, updateProfile } from '../api/auth';
import ConfirmDialog from '../components/ConfirmDialog';
import PasswordField from '../components/PasswordField';
import { useAuth } from '../hooks/AuthContext';
import { errorMessage, fieldErrors } from '../utils/errors';

/** Run one settings request and report the result as `{ ok }` or `{ errors }` keyed by field. */
async function submit(request) {
  try {
    return { ok: true, result: await request() };
  } catch (err) {
    const byField = fieldErrors(err);
    if (err?.status === 409) byField.email = 'An account with this email already exists.';
    return { ok: false, errors: Object.keys(byField).length ? byField : { form: errorMessage(err) } };
  }
}

function Notice({ saved, error }) {
  if (error) {
    return (
      <p className="field-error" role="alert">
        {error}
      </p>
    );
  }
  return saved ? <p className="field-ok" role="status">Saved.</p> : null;
}

function ProfileForm() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user.full_name ?? '');
  const [state, setState] = useState({});

  async function onSubmit(event) {
    event.preventDefault();
    const res = await submit(() => updateProfile({ full_name: name }));
    if (res.ok) setUser(res.result);
    setState(res.ok ? { saved: true } : { error: res.errors.full_name ?? res.errors.form });
  }

  return (
    <form className="card settings-card" onSubmit={onSubmit} noValidate>
      <h2>Profile</h2>
      <div className="field">
        <label htmlFor="full_name">Full name</label>
        <input id="full_name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
      </div>
      <Notice {...state} />
      <button type="submit" className="btn btn-primary">Save profile</button>
    </form>
  );
}

function EmailForm() {
  const { user, setUser } = useAuth();
  const [email, setEmail] = useState(user.email);
  const [current, setCurrent] = useState('');
  const [state, setState] = useState({});

  async function onSubmit(event) {
    event.preventDefault();
    const res = await submit(() => updateProfile({ email, current_password: current }));
    if (res.ok) {
      setUser(res.result);
      setCurrent('');
      setState({ saved: true });
    } else {
      setState({ errors: res.errors });
    }
  }

  const errors = state.errors ?? {};
  return (
    <form className="card settings-card" onSubmit={onSubmit} noValidate>
      <h2>Email address</h2>
      <div className="field">
        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" aria-invalid={errors.email ? 'true' : undefined} />
        {errors.email && <p className="field-error">{errors.email}</p>}
      </div>
      <PasswordField id="email-password" label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" error={errors.current_password && `Your password ${errors.current_password}.`} />
      <Notice saved={state.saved} error={errors.form} />
      <button type="submit" className="btn btn-primary">Update email</button>
    </form>
  );
}

function PasswordForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [state, setState] = useState({});

  async function onSubmit(event) {
    event.preventDefault();
    const res = await submit(() => updateProfile({ new_password: next, current_password: current }));
    if (res.ok) {
      setCurrent('');
      setNext('');
      setState({ saved: true });
    } else {
      setState({ errors: res.errors });
    }
  }

  const errors = state.errors ?? {};
  return (
    <form className="card settings-card" onSubmit={onSubmit} noValidate>
      <h2>Password</h2>
      <PasswordField id="old-password" label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" error={errors.current_password && `Your password ${errors.current_password}.`} />
      <PasswordField id="new-password" label="New password" value={next} onChange={setNext} autoComplete="new-password" error={errors.new_password} hint="At least 8 characters." />
      <Notice saved={state.saved} error={errors.form} />
      <button type="submit" className="btn btn-primary">Change password</button>
    </form>
  );
}

function DeleteAccount() {
  const { user, logout } = useAuth();
  const doctor = user.role === 'doctor';
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  async function onConfirm() {
    setPending(true);
    const res = await submit(() => deleteAccount(password));
    if (res.ok) {
      logout();
      navigate('/', { replace: true });
      return;
    }
    setPending(false);
    setError(res.errors.password ? `Your password ${res.errors.password}.` : (res.errors.form ?? 'Could not delete the account.'));
  }

  function close() {
    setOpen(false);
    setPassword('');
    setError(null);
  }

  return (
    <section className="card settings-card danger-zone" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete account</h2>
      <p className="muted">
        {doctor
          ? 'This removes your login. Your doctor profile and all bookings stay, and an administrator can give you a new login later.'
          : 'This removes your login and personal settings. Bookings you already made stay on the clinic’s schedule.'}
      </p>
      <button type="button" className="btn btn-danger-outline" onClick={() => setOpen(true)}>
        Delete my account
      </button>
      {open && (
        <ConfirmDialog
          title="Delete your account?"
          confirmLabel="Delete account"
          pending={pending}
          onConfirm={onConfirm}
          onCancel={close}
        >
          <span>This cannot be undone. Enter your password to confirm.</span>
          <PasswordField id="delete-password" label="Password" value={password} onChange={setPassword} autoComplete="current-password" error={error} />
        </ConfirmDialog>
      )}
    </section>
  );
}

/** Account settings. Patients and doctors can delete their login; admins cannot. */
export default function AccountPage() {
  const { user } = useAuth();
  return (
    <div className="container narrow">
      <h1 className="page-title">Account settings</h1>
      <div className="settings">
        <ProfileForm />
        <EmailForm />
        <PasswordForm />
        {user.role === 'admin' ? (
          <p className="muted">Administrator accounts cannot be deleted here.</p>
        ) : (
          <DeleteAccount />
        )}
      </div>
    </div>
  );
}
