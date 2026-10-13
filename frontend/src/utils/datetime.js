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
