import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import Footer from './Footer';
import logoUrl from '../../logo/Logo.jpeg';

function Logo() {
  return (
    <Link to="/" className="brand">
      {/* The full logo is a square with the name underneath, so show only its emblem here. */}
      <span className="brand-mark" aria-hidden="true">
        <img src={logoUrl} alt="" />
      </span>
      DocEase
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
            <NavLink to="/book">Doctor Channelling</NavLink>
            {user?.role === 'patient' && <NavLink to="/my-bookings">My bookings</NavLink>}
            {user && user.role !== 'patient' && <NavLink to="/appointments">Appointments</NavLink>}
            {user && user.role !== 'patient' && <NavLink to="/patients">Patients</NavLink>}
            {user?.role === 'admin' && <NavLink to="/admin/doctors">Doctors</NavLink>}
            {user?.role === 'doctor' && <NavLink to="/my-schedule">My schedule</NavLink>}
          </nav>
          <div className="header-actions">
            {user ? (
              <>
                <Link to="/account" className="user-chip" title={user.email}>
                  <span className="avatar" aria-hidden="true">{(user.full_name ?? user.email).slice(0, 2).toUpperCase()}</span>
                  <span className="role">{user.full_name ?? user.role}</span>
                  <span className="sr-only"> (account settings)</span>
                </Link>
                <button type="button" className="btn btn-secondary" onClick={logout}>Sign out</button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn-secondary">Sign in</Link>
                <Link to="/signup" className="btn btn-primary">Sign up</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
