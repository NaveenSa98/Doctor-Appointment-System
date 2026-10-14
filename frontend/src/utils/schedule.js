export const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const pad = (n) => String(n).padStart(2, '0');

/** Clinic clock label, e.g. 330 -> "UTC+05:30", 0 -> "UTC". */
export function formatOffset(minutes) {
  if (!minutes) return 'UTC';
  const sign = minutes < 0 ? '-' : '+';
  const abs = Math.abs(minutes);
  return `UTC${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

/** "00:00", "00:30", ... "23:30" for the time pickers. */
export const HALF_HOURS = Array.from({ length: 48 }, (_, i) => `${pad(Math.floor(i / 2))}:${i % 2 ? '30' : '00'}`);

/** A `YYYY-MM-DD` clinic date as a readable local string, e.g. "Mon, 20 Oct 2026". */
export function formatDay(day) {
  const [y, m, d] = day.split('-').map(Number);
  return new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(
    new Date(y, m - 1, d),
  );
}

/** Sessions grouped by weekday (Monday first), each day's sessions in time order. */
export function groupByWeekday(sessions) {
  return WEEKDAYS.map((name, weekday) => ({
    weekday,
    name,
    sessions: sessions.filter((s) => s.weekday === weekday).sort((a, b) => a.start_time.localeCompare(b.start_time)),
  })).filter((group) => group.sessions.length > 0);
}
