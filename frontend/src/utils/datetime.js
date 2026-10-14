const pad = (n) => String(n).padStart(2, '0');

/**
 * Convert a local `YYYY-MM-DDTHH:mm` value (datetime-local input) to a UTC ISO string.
 * A time that does not exist (DST gap) is moved forward by the browser's rules.
 * @param {string} local
 * @returns {string}
 */
export function localToUtcIso(local) {
  return new Date(local).toISOString();
}

/**
 * Convert a UTC ISO string to a local `YYYY-MM-DDTHH:mm` value for a datetime-local input.
 * @param {string} iso
 * @returns {string}
 */
export function utcIsoToLocalInput(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Human-readable local date and time, e.g. "Thu, 15 Oct, 10:30".
 * @param {string} iso UTC ISO string
 * @returns {string}
 */
export function formatDateTime(iso) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso));
}

/**
 * UTC bounds of a local calendar day: `from` inclusive, `to` exclusive (next local midnight).
 * @param {string} date local `YYYY-MM-DD`
 * @returns {{ from: string, to: string }}
 */
export function localDayRange(date) {
  const [y, m, d] = date.split('-').map(Number);
  return { from: new Date(y, m - 1, d).toISOString(), to: new Date(y, m - 1, d + 1).toISOString() };
}

/** Move a local `YYYY-MM-DD` by whole days. */
export function shiftDate(date, days) {
  const [y, m, d] = date.split('-').map(Number);
  const next = new Date(y, m - 1, d + days);
  return `${next.getFullYear()}-${pad(next.getMonth() + 1)}-${pad(next.getDate())}`;
}

/** The viewer's IANA time zone, e.g. "Asia/Colombo". */
export const localTimeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

/**
 * Full local date and time with the zone, for printed receipts,
 * e.g. "Thursday, 15 October 2026, 10:30 GMT+5:30".
 * @param {string} iso UTC ISO string
 * @returns {string}
 */
export function formatFullDateTime(iso) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(iso));
}
