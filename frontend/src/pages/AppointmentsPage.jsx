import { Link } from 'react-router-dom';
import AppointmentFiltersfrom '../components/AppointmentFilters';
import AppointmentTable from '../components/AppointmentTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Pagination from '../components/Pagination';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { PAGE_SIZE, useAppointments } from '../hooks/useAppointments';
import { useDoctors, useHospitals } from '../hooks/useDoctors';
import { useUrlFilters } from '../hooks/useUrlFilters';

/** Staff list: search, filters, sort and pagination, all kept in the URL. */
export default function AppointmentsPage() {
  const { user } = useAuth();
  const { filters, setFilters, clearFilters, hasActiveFilters } = useUrlFilters();
  const { data, error, isPending, isError, isPlaceholderData, refetch } = useAppointments(filters);
  const doctors = useDoctors();
  const hospitals = useHospitals();

  let body;
  if (isPending) body = <Spinner label="Loading appointments" />;
  else if (isError && !data) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.items.length === 0) {
    body = hasActiveFilters ? (
      <EmptyState title="No appointments match your filters">
        <button type="button" className="btn btn-secondary" onClick={clearFilters}>
          Clear filters
        </button>
      </EmptyState>
    ) : (
      <EmptyState title="No appointments yet">New bookings will appear here.</EmptyState>
    );
  } else {
    body = (
      <div className={isPlaceholderData ? 'dim' : undefined} aria-busy={isPlaceholderData}>
        <AppointmentTable items={data.items} sort={filters.sort} onSort={(sort) => setFilters({ sort })} />
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          pageSize={PAGE_SIZE}
          onPage={(page) => setFilters({ page })}
        />
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-head">
        <h1 className="page-title">Appointments</h1>
        <Link to="/appointments/new" className="btn btn-primary">
          New appointment
        </Link>
      </div>
      <section className="card list-card" aria-label="Appointment list">
        <AppointmentFilters
          filters={filters}
          onChange={setFilters}
          doctors={doctors.data}
          hospitals={hospitals.data}
          showDoctor={user?.role !== 'doctor'}
        />
        {body}
      </section>
    </div>
  );
}
