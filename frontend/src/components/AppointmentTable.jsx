import { Link } from 'react-router-dom';
import { formatDateTime } from '../utils/datetime';
import StatusBadge from './StatusBadge';

const humanize = (s) => s.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

function SortHeader({ field, label, sort, onSort }) {
  const active = sort === field || sort === `-${field}`;
  const desc = sort === `-${field}`;
  return (
    <th scope="col" aria-sort={active ? (desc ? 'descending' : 'ascending') : 'none'}>
      <button type="button" className="sort-btn" onClick={() => onSort(sort === field ? `-${field}` : field)}>
        {label}
        <span aria-hidden="true">{active ? (desc ? ' ↓' : ' ↑') : ''}</span>
      </button>
    </th>
  );
}

/** Appointment rows with sortable Patient and When columns. */
export default function AppointmentTable({ items, sort, onSort }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <SortHeader field="patient_name" label="Patient" sort={sort} onSort={onSort} />
            <th scope="col">Doctor</th>
            <th scope="col">Hospital</th>
            <SortHeader field="start_time" label="When" sort={sort} onSort={onSort} />
            <th scope="col">Type</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.id}>
              <td className="strong">
                <Link to={`/appointments/${a.id}`}>{a.patient_name}</Link>
              </td>
              <td>
                {a.doctor.full_name}
                <div className="sub">{a.doctor.specialty}</div>
              </td>
              <td>{a.hospital.name}</td>
              <td>{formatDateTime(a.start_time)}</td>
              <td>{humanize(a.appointment_type)}</td>
              <td><StatusBadge status={a.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
