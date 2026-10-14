import { useMemo, useState } from 'react';
import { useDoctors, useHospitals } from '../hooks/useDoctors';
import { filterDoctors, specialtiesOf } from '../utils/doctorSearch';
import { todayLocal } from '../utils/slots';

const EMPTY = { name: '', specialty: '', hospitalId: '', date: '' };

/**
 * Search bar for finding a doctor by name, specialization, hospital and date, with the
 * matching doctors listed underneath. `onChoose({ doctorId, hospitalId, date })` fills the form.
 */
export default function DoctorSearch({ onChoose }) {
  const doctors = useDoctors();
  const hospitals = useHospitals();
  const [fields, setFields] = useState(EMPTY);
  const [applied, setApplied] = useState(null); // null until the first search

  const specialties = useMemo(() => specialtiesOf(doctors.data ?? []), [doctors.data]);
  const results = useMemo(
    () => (applied ? filterDoctors(doctors.data ?? [], applied) : []),
    [applied, doctors.data],
  );
  const set = (key) => (event) => setFields((f) => ({ ...f, [key]: event.target.value }));

  function submit(event) {
    event.preventDefault();
    setApplied({ ...fields });
  }

  function clear() {
    setFields(EMPTY);
    setApplied(null);
  }

  function choose(doctor) {
    const only = doctor.hospitals.length === 1 ? doctor.hospitals[0].id : '';
    onChoose({ doctorId: doctor.id, hospitalId: applied.hospitalId || only, date: applied.date });
  }

  const hospitalName = (id) => hospitals.data?.find((h) => h.id === id)?.name;

  return (
    <section aria-label="Find a doctor" className="doctor-search">
      <form role="search" className="search-panel" onSubmit={submit}>
        <div className="search-cell search-cell-name">
          <label htmlFor="ds-name">Doctor name</label>
          <input id="ds-name" type="search" maxLength={100} placeholder="Search doctor name" value={fields.name} onChange={set('name')} />
        </div>
        <div className="search-cell">
          <label htmlFor="ds-specialty">Specialization</label>
          <select id="ds-specialty" value={fields.specialty} onChange={set('specialty')}>
            <option value="">Select specialization</option>
            {specialties.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="search-cell">
          <label htmlFor="ds-hospital">Filter by hospital</label>
          <select id="ds-hospital" value={fields.hospitalId} onChange={set('hospitalId')}>
            <option value="">Select hospital</option>
            {(hospitals.data ?? []).map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </select>
        </div>
        <div className="search-cell">
          <label htmlFor="ds-date">Preferred date</label>
          <input id="ds-date" type="date" min={todayLocal()} value={fields.date} onChange={set('date')} />
        </div>
        <div className="search-actions">
          <button type="submit" className="btn search-btn">
            Search
          </button>
          {applied && (
            <button type="button" className="search-clear" onClick={clear}>
              Clear
            </button>
          )}
        </div>
      </form>

      {applied && (
        <div className="search-results">
          <p role="status" className="search-count">
            {results.length === 0
              ? 'No doctors match your search. Try fewer filters.'
              : `${results.length} ${results.length === 1 ? 'doctor' : 'doctors'} found`}
          </p>
          <ul>
            {results.map((doctor) => (
              <li key={doctor.id} className="doctor-card">
                <div>
                  <h3>{doctor.full_name}</h3>
                  <span className="sub">{doctor.specialty}</span>
                  <span className="sub">
                    {applied.hospitalId
                      ? hospitalName(applied.hospitalId)
                      : doctor.hospitals.map((h) => h.name).join(', ')}
                  </span>
                </div>
                <button type="button" className="btn btn-primary" onClick={() => choose(doctor)} aria-label={`Book with ${doctor.full_name}`}>
                  Book
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
