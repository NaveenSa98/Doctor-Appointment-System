import { localToUtcIso } from './datetime';

// Bookable day: 09:00 to 16:30, every 30 minutes (the API only requires :00 or :30).
export const FIRST_HOUR = 9;
export const LAST_HOUR = 16;

const pad = (n) => String(n).padStart(2, '0');

/**
 * Slots for a local date.
 * @param {string} date local `YYYY-MM-DD`
 * @returns {string[]} UTC ISO start times
 */
export function slotsForDate(date) {
  const out = [];
  for (let h = FIRST_HOUR; h <= LAST_HOUR; h += 1) {
    for (const m of [0, 30]) out.push(localToUtcIso(`${date}T${pad(h)}:${pad(m)}`));
  }
  return out;
}

/** Local time label for a slot, e.g. "10:30". */
export function slotLabel(iso) {
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', hour12: false }).format(
    new Date(iso),
  );
}

/** Local `YYYY-MM-DD` for today. */
export function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
