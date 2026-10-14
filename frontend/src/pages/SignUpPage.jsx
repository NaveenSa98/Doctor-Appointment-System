import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import AuthShell from '../components/AuthShell';
import PasswordField from '../components/PasswordField';
import { useAuth } from '../hooks/AuthContext';
import { errorMessage, fieldErrors } from '../utils/errors';
import { homeFor } from '../utils/roles';

const POINTS = [
  'Book a visit in under a minute',
  'See all your past and upcoming bookings',
  'Your details are yours: edit or delete them any time',
];

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function validate({ fullName, email, password, confirm }) {
  const errors = {};
  if (fullName.trim().length < 2) errors.full_name = 'Enter your full name (at least 2 characters).';
  if (!EMAIL_RE.test(email.trim())) errors.email = 'Enter a valid email address.';
  if (password.length < 8) errors.password = 'Use at least 8 characters.';
  if (confirm !== password) errors.confirm = 'The passwords do not match.';
  return errors;
}

export default function SignUpPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname;

  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [pending, setPending] = useState(false);

  if (user && !pending) return <Navigate to={from ?? homeFor(user.role)} replace />;

  const set = (key) => (value) => setForm((f) => ({ ...f, [key]: value }));

  async function onSubmit(event) {
    event.preventDefault();
    if (pending) return;
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setPending(true);
    try {
      const me = await register(form.fullName.trim(), form.email.trim(), form.password);
      navigate(from ?? homeFor(me.role), { replace: true });
    } catch (err) {
      setErrors(
        err?.status === 409
          ? { email: 'An account with this email already exists. Try signing in instead.' }
          : { ...fieldErrors(err), form: Object.keys(fieldErrors(err)).length ? undefined : errorMessage(err) },
      );
      setPending(false);
    }
  }

  const invalid = (key) => (errors[key] ? 'true' : undefined);

  return (
    <AuthShell
      headline="Your health, organised."
      text="Create a free patient account to book faster and keep track of every visit."
      points={POINTS}
    >
      <form className="signin-form" onSubmit={onSubmit} noValidate>
        <div>
          <h1>Create your account</h1>
          <p className="muted">It takes less than a minute.</p>
        </div>

        {errors.form && (
          <div className="alert" role="alert">
            {errors.form}
          </div>
        )}

        <div className="field">
          <label htmlFor="full_name">Full name</label>
          <input
            id="full_name"
            type="text"
            autoComplete="name"
            value={form.fullName}
            onChange={(e) => set('fullName')(e.target.value)}
            aria-invalid={invalid('full_name')}
            aria-describedby={errors.full_name ? 'full_name-note' : undefined}
            required
          />
          {errors.full_name && (
            <p id="full_name-note" className="field-error">
              {errors.full_name}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={(e) => set('email')(e.target.value)}
            aria-invalid={invalid('email')}
            aria-describedby={errors.email ? 'email-note' : undefined}
            required
          />
          {errors.email && (
            <p id="email-note" className="field-error">
              {errors.email}
            </p>
          )}
        </div>

        <PasswordField
          id="password"
          label="Password"
          autoComplete="new-password"
          value={form.password}
          onChange={set('password')}
          error={errors.password}
          hint="At least 8 characters."
        />
        <PasswordField
          id="confirm"
          label="Confirm password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={set('confirm')}
          error={errors.confirm}
        />

        <button type="submit" className="btn btn-primary btn-lg" disabled={pending}>
          {pending ? 'Creating account…' : 'Create account'}
        </button>

        <p className="signin-alt">
          Already have an account? <Link to="/login" state={location.state}>Sign in</Link>
        </p>
      </form>
    </AuthShell>
  );
}
