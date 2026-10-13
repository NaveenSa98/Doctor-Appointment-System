import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import AppointmentsPage from './pages/AppointmentsPage';
import NotFoundPage from './pages/NotFoundPage';
import ComingSoonPage from './pages/ComingSoonPage';

/** Public: /, /book, /book/confirmed, /login. Staff only: /appointments, /appointments/:id. */
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="book" element={<ComingSoonPage title="Book an appointment" />} />
        <Route path="book/confirmed" element={<ComingSoonPage title="Booking confirmed" />} />
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="appointments/:id" element={<ComingSoonPage title="Appointment" />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
