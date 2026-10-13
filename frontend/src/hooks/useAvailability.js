import { useQuery } from '@tanstack/react-query';
import { getAvailability } from '../api/doctors';
import { localToUtcIso } from '../utils/datetime';

/** Next local midnight after `date`, as UTC ISO (the exclusive end of that local day). */
function nextDayStart(date) {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(y, m - 1, d + 1).toISOString();
}

/** Taken start times for a doctor on a local date. Disabled until both are chosen. */
export function useAvailability(doctorId, date) {
  return useQuery({
    queryKey: ['availability', doctorId, date],
    queryFn: () =>
      getAvailability(doctorId, { date_from: localToUtcIso(`${date}T00:00`), date_to: nextDayStart(date) }),
    enabled: Boolean(doctorId && date),
  });
}
