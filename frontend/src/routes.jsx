import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AppointmentFormPage from './pages/AppointmentFormPage';
import AppointmentsPage from './pages/AppointmentsPage';
import BookingConfirmedPage from './pages/BookingConfirmedPage';
import BookingPage from './pages/BookingPage';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';

/** Public: /, /book, /book/confirmed, /login. Staff only: /appointments, /appointments/new, /appointments/:id. */
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="book" element={<BookingPage />} />
        <Route path="book/confirmed" element={<BookingConfirmedPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="appointments/new" element={<AppointmentFormPage />} />
          <Route path="appointments/:id" element={<AppointmentFormPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
