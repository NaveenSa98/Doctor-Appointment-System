import { localToUtcIso, utcIsoToLocalInput } from '../utils/datetime';

// vite.config.js pins TZ to America/New_York.
describe('datetime', () => {
  it('round-trips local -> UTC -> local', () => {
    const local = '2026-10-15T10:30';
    const iso = localToUtcIso(local);
    expect(iso).toBe('2026-10-15T14:30:00.000Z'); // EDT is UTC-4
    expect(utcIsoToLocalInput(iso)).toBe(local);
  });

  it('moves a time inside the DST gap forward and stays stable afterwards', () => {
    const gap = '2026-03-08T02:30'; // does not exist in New York
    const once = utcIsoToLocalInput(localToUtcIso(gap));
    expect(once).toBe('2026-03-08T03:30');
    expect(utcIsoToLocalInput(localToUtcIso(once))).toBe(once);
  });
});
