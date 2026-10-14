import { formatDay, groupByWeekday } from '../utils/schedule';

/**
 * A doctor's weekly sessions, grouped by day. `actions(session)` can add buttons to each row
 * (the admin manager does); the doctor's own page leaves it out, so it is read-only.
 */
export default function WeeklySchedule({ sessions, actions }) {
  return (
    <div className="week">
      {groupByWeekday(sessions).map((group) => (
        <section key={group.weekday} className="week-day" aria-label={group.name}>
          <h3>{group.name}</h3>
          <ul>
            {group.sessions.map((s) => (
              <li key={s.id}>
                <div className="session-main">
                  <strong>
                    {s.start_time}–{s.end_time}
                  </strong>
                  <span className="sub">{s.hospital.name}</span>
                  {s.skipped.length > 0 && (
                    <ul className="skipped" aria-label="Skipped dates">
                      {s.skipped.map((x) => (
                        <li key={x.on_date}>
                          <span>
                            Not running on {formatDay(x.on_date)}
                            {x.reason ? ` (${x.reason})` : ''}
                          </span>
                          {actions?.restore(s, x)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                {actions?.row(s)}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
