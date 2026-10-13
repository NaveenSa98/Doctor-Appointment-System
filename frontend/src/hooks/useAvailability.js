import { useQuery } from '@tanstack/react-query';
import { getAvailability } from '../api/doctors';
import { localDayRange } from '../utils/datetime';

/** Taken start times for a doctor on a local date. Disabled until both are chosen. */
export function useAvailability(doctorId, date) {
  return useQuery({
    queryKey: ['availability', doctorId, date],
    queryFn: () => {
      const { from, to } = localDayRange(date);
      return getAvailability(doctorId, { date_from: from, date_to: to });
    },
    enabled: Boolean(doctorId && date),
  });
}
