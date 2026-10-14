import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import AuthShell from '../components/AuthShell';
import PasswordField from '../components/PasswordField';
import { useAuth } from '../hooks/AuthContext';
import { errorMessage } from '../utils/errors';
import { homeFor } from '../utils/roles';

const POINTS = [
  'See your bookings and your schedule in one place',
  'Change a status in a single click',
  'Never double-booked, whatever the hour',
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  if (user && !pending) return <Navigate to={from ?? homeFor(user.role)} replace />;

  async function onSubmit(event) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const me = await login(email, password);
      navigate(from ?? homeFor(me.role), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setPending(false);
    }
  }

  return (
    <AuthShell
      headline="Care that runs on time."
      text="Sign in to manage your appointments, schedule and bookings."
      points={POINTS}
    >
      <form className="signin-form" onSubmit={onSubmit} noValidate>
        <div>
          <h1>Welcome back</h1>
          <p className="muted">Sign in to manage your appointments and schedule.</p>
        </div>

        {error && (
          <div className="alert" role="alert">
            {error}
          </div>
        )}

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={error ? 'true' : undefined}
            required
          />
        </div>

        <PasswordField
          id="password"
          label="Password"
          autoComplete="current-password"
          value={password}
          onChange={setPassword}
          invalid={Boolean(error)}
        />

        <button type="submit" className="btn btn-primary btn-lg" disabled={pending}>
          {pending ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="signin-alt">
          New to DocEase? <Link to="/signup" state={location.state}>Create an account</Link>
        </p>

        <div className="signin-divider">or</div>

        <Link to="/book" className="signin-guest">
          <span>
            <strong>Just need to see a doctor?</strong>
            <span>Book an appointment as a guest, no account needed.</span>
          </span>
        </Link>
      </form>
    </AuthShell>
  );
}
