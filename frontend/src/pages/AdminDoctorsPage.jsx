import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Spinner from '../components/Spinner';
import { useAdminDoctors } from '../hooks/useAdminDoctors';

function ActiveBadge({ active }) {
  return <span className={active ? 'badge badge-confirmed' : 'badge badge-no_show'}>{active ? 'Active' : 'Inactive'}</span>;
}

/** Admin list of every doctor with their login, hospitals and booking count. */
export default function AdminDoctorsPage() {
  const { data, error, isPending, isError, refetch } = useAdminDoctors();

  let body;
  if (isPending) body = <Spinner label="Loading doctors" />;
  else if (isError) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.length === 0) {
    body = (
      <EmptyState title="No doctors yet">
        <Link to="/admin/doctors/new" className="btn btn-primary">
          Add the first doctor
        </Link>
      </EmptyState>
    );
  } else {
    body = (
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Doctor</th>
              <th scope="col">Hospitals</th>
              <th scope="col">Login</th>
              <th scope="col">Bookings</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.id}>
                <td className="strong">
                  <Link to={`/admin/doctors/${d.id}`}>{d.full_name}</Link>
                  <div className="sub">{d.specialty}</div>
                </td>
                <td>{d.hospitals.map((h) => h.name).join(', ')}</td>
                <td>{d.account ? d.account.email : <span className="sub">No login yet</span>}</td>
                <td>{d.appointment_count}</td>
                <td>
                  <ActiveBadge active={d.is_active} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="page-head">
        <h1 className="page-title">Doctors</h1>
        <Link to="/admin/doctors/new" className="btn btn-primary">
          Add doctor
        </Link>
      </div>
      <section className="card list-card" aria-label="Doctor list">
        {body}
      </section>
    </div>
  );
}
