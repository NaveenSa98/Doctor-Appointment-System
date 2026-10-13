import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listAppointments } from '../api/appointments';

export const PAGE_SIZE = 20;

/** Paged appointment list. Keeps the previous page on screen while the next one loads. */
export function useAppointments(filters) {
  const params = {
    q: filters.q,
    status: filters.status,
    doctor_id: filters.doctor_id,
    hospital_id: filters.hospital_id,
    sort: filters.sort,
    page: filters.page,
    page_size: PAGE_SIZE,
  };
  return useQuery({
    queryKey: ['appointments', params],
    queryFn: () => listAppointments(params),
    placeholderData: keepPreviousData,
  });
}
