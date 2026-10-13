import { Link } from 'react-router-dom';
import { localTimeZone } from '../utils/datetime';
import { slotLabel } from '../utils/slots';
import { TYPES } from './AppointmentForm';
import StatusBadge from './StatusBadge';

/** Group time-sorted appointments by doctor (alphabetical), keeping each doctor's time order. */
export function groupByDoctor(items) {
  const groups = new Map();
  for (const a of items) {
    if (!groups.has(a.doctor.id)) groups.set(a.doctor.id, { doctor: a.doctor, items: [] });
    groups.get(a.doctor.id).items.push(a);
  }
  return [...groups.values()].sort((a, b) => a.doctor.full_name.localeCompare(b.doctor.full_name));
}

/** Simple agenda: one block per doctor, times in the viewer's local zone. */
export default function DayView({ items }) {
  return (
    <div>
      <p className="muted tz-note">Times shown in {localTimeZone()}</p>
      <div className="agenda">
        {groupByDoctor(items).map(({ doctor, items: rows }) => (
          <section key={doctor.id} className="card agenda-group" aria-labelledby={`doc-${doctor.id}`}>
            <h2 id={`doc-${doctor.id}`}>
              {doctor.full_name} <span className="sub">{doctor.specialty}</span>
            </h2>
            <ul>
              {rows.map((a) => (
                <li key={a.id}>
                  <time dateTime={a.start_time}>{slotLabel(a.start_time)}</time>
                  <span className="agenda-main">
                    <Link to={`/appointments/${a.id}`}>{a.patient_name}</Link>
                    <span className="sub">
                      {TYPES[a.appointment_type] ?? a.appointment_type} · {a.hospital.name}
                    </span>
                  </span>
                  <StatusBadge status={a.status} />
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
