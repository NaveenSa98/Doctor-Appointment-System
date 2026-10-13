import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getStats } from '../api/appointments';

/** Counts per status. `doctorId` follows the list's doctor filter. */
export function useStats(doctorId) {
  const params = { doctor_id: doctorId };
  return useQuery({
    queryKey: ['appointment-stats', params],
    queryFn: () => getStats(params),
    placeholderData: keepPreviousData,
  });
}
