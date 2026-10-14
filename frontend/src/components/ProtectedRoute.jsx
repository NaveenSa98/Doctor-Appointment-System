import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import { homeFor } from '../utils/roles';
import Spinner from './Spinner';

/**
 * Sign-in wrapper: sends visitors to /login and remembers where they were going.
 * With `roles`, a signed-in user of another kind is sent to their own home page.
 */
export default function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}
