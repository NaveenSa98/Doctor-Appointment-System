import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listPatients } from '../api/patients';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import Pagination from '../components/Pagination';
import Spinner from '../components/Spinner';
import { useAuth } from '../hooks/AuthContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { formatDateTime } from '../utils/datetime';

const PAGE_SIZE = 20;

/** Registered patients. Admins see everyone; doctors see patients who booked with them. */
export default function PatientsPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const page = Math.max(1, Number.parseInt(params.get('page') ?? '1', 10) || 1);

  const [search, setSearch] = useState(q);
  const debounced = useDebouncedValue(search, 300);

  // Push the debounced text to the URL (back to page 1), then follow outside changes.
  useEffect(() => {
    if (debounced.trim() !== q) setParams(debounced.trim() ? { q: debounced.trim() } : {}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);
  useEffect(() => {
    if (q !== debounced.trim()) setSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const { data, error, isPending, isError, isPlaceholderData, refetch } = useQuery({
    queryKey: ['patients', { q, page }],
    queryFn: () => listPatients({ q, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  let body;
  if (isPending) body = <Spinner label="Loading patients" />;
  else if (isError && !data) body = <ErrorState error={error} onRetry={refetch} />;
  else if (data.items.length === 0) {
    body = q ? (
      <EmptyState title="No patients match your search" />
    ) : (
      <EmptyState title="No registered patients yet">Patients who create an account appear here.</EmptyState>
    );
  } else {
    body = (
      <div className={isPlaceholderData ? 'dim' : undefined} aria-busy={isPlaceholderData}>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Patient</th>
                <th scope="col">Email</th>
                <th scope="col">Bookings</th>
                <th scope="col">Latest booking</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id}>
                  <td className="strong">
                    <Link to={`/patients/${p.id}`}>{p.full_name ?? p.email}</Link>
                    {!p.is_active && <span className="sub">Inactive</span>}
                  </td>
                  <td>{p.email}</td>
                  <td>{p.booking_count}</td>
                  <td>{p.last_booking_at ? formatDateTime(p.last_booking_at) : '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          pageSize={PAGE_SIZE}
          onPage={(next) => setParams({ ...(q && { q }), ...(next > 1 && { page: String(next) }) })}
        />
      </div>
    );
  }

  return (
    <div className="container">
      <h1 className="page-title">Patients</h1>
      <p className="muted lede">
        {user?.role === 'doctor'
          ? 'Patients with an account who have booked with you.'
          : 'Everyone who has created a patient account. Guest bookings are not listed here.'}
      </p>
      <section className="card list-card" aria-label="Patient list">
        <form role="search" className="filters" onSubmit={(e) => e.preventDefault()}>
          <div className="search-field">
            <label htmlFor="patient-q" className="sr-only">
              Search patients by name or email
            </label>
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-4-4" />
            </svg>
            <input id="patient-q" type="search" maxLength={100} placeholder="Search by name or email" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </form>
        {body}
      </section>
    </div>
  );
}
