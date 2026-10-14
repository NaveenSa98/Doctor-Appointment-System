import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';

function Logo() {
  return (
    <Link to="/" className="brand">
      <span className="brand-mark" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </span>
      Appointment Manager
    </Link>
  );
}

/** App shell: header (Sign in or user menu) and the routed page. */
export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <header className="header">
        <div className="header-inner">
          <Logo />
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/book">Book a visit</NavLink>
            {user && <NavLink to="/appointments">Appointments</NavLink>}
          </nav>
          <div className="header-actions">
            {user ? (
              <>
                <span className="user-chip" title={user.email}>
                  <span className="avatar" aria-hidden="true">{user.email.slice(0, 2).toUpperCase()}</span>
                  <span className="role">{user.role}</span>
                </span>
                <button type="button" className="btn btn-secondary" onClick={logout}>Sign out</button>
              </>
            ) : (
              <Link to="/login" className="btn btn-secondary">Sign in</Link>
            )}
          </div>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
