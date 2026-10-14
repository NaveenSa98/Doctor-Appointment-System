import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import { errorMessage } from '../utils/errors';
import logoUrl from '../../logo/Logo.jpeg';

const POINTS = [
  'See your day and your patients in one place',
  'Change a status in a single click',
  'Never double-booked, whatever the hour',
];

function Tick() {
  return (
    <span className="tick" aria-hidden="true">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12l5 5 9-10" />
      </svg>
    </span>
  );
}

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname ?? '/appointments';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  if (user && !pending) return <Navigate to={redirectTo} replace />;

  async function onSubmit(event) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      await login(email, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setPending(false);
    }
  }

  return (
    <div className="signin">
      <div className="signin-shell">
        <aside className="signin-aside">
          <img src={logoUrl} alt="DocEase" />
          <div>
            <h2>Care that runs on time.</h2>
            <p>Sign in to manage appointments, schedules and patients across your hospitals.</p>
          </div>
          <ul className="signin-points">
            {POINTS.map((text) => (
              <li key={text}>
                <Tick />
                {text}
              </li>
            ))}
          </ul>
        </aside>

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

          <div className="field">
            <label htmlFor="password">Password</label>
            <div className="input-wrap">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={error ? 'true' : undefined}
                required
              />
              <button
                type="button"
                className="input-toggle"
                aria-pressed={showPassword}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-lg" disabled={pending}>
            {pending ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="signin-divider">or</div>

          <Link to="/book" className="signin-guest">
            <span>
              <strong>Just need to see a doctor?</strong>
              <span>Book an appointment as a guest, no account needed.</span>
            </span>
          </Link>
        </form>
      </div>
    </div>
  );
}
