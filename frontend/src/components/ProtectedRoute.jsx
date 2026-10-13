import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import Spinner from './Spinner';

/** Staff-only wrapper: sends visitors to /login and remembers where they were going. */
export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner label="Checking your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
