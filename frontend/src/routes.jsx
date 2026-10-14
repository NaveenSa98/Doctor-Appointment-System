import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AccountPage from './pages/AccountPage';
import AdminDoctorFormPage from './pages/AdminDoctorFormPage';
import AdminDoctorsPage from './pages/AdminDoctorsPage';
import AppointmentFormPage from './pages/AppointmentFormPage';
import AppointmentsPage from './pages/AppointmentsPage';
import BookingConfirmedPage from './pages/BookingConfirmedPage';
import BookingPage from './pages/BookingPage';
import DayViewPage from './pages/DayViewPage';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MyBookingsPage from './pages/MyBookingsPage';
import NotFoundPage from './pages/NotFoundPage';
import SignUpPage from './pages/SignUpPage';
import { STAFF_ROLES } from './utils/roles';

/**
 * Public: /, /book, /book/confirmed, /login, /signup.
 * Patients: /my-bookings. Staff (admin, doctor): /appointments, /appointments/day, /new, /:id.
 * Any signed-in user: /account.
 */
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="book" element={<BookingPage />} />
        <Route path="book/confirmed" element={<BookingConfirmedPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignUpPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="account" element={<AccountPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['patient']} />}>
          <Route path="my-bookings" element={<MyBookingsPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={STAFF_ROLES} />}>
          <Route path="appointments" element={<AppointmentsPage />} />
          <Route path="appointments/day" element={<DayViewPage />} />
          <Route path="appointments/new" element={<AppointmentFormPage />} />
          <Route path="appointments/:id" element={<AppointmentFormPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route path="admin/doctors" element={<AdminDoctorsPage />} />
          <Route path="admin/doctors/new" element={<AdminDoctorFormPage />} />
          <Route path="admin/doctors/:id" element={<AdminDoctorFormPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
