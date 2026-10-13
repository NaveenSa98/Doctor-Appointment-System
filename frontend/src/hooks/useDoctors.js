import { useQuery } from '@tanstack/react-query';
import { listDoctors, listHospitals } from '../api/doctors';

/** Active doctors, for filter dropdowns. */
export function useDoctors() {
  return useQuery({ queryKey: ['doctors'], queryFn: () => listDoctors(), staleTime: 5 * 60_000 });
}

/** Hospitals, for filter dropdowns. */
export function useHospitals() {
  return useQuery({
    queryKey: ['hospitals'],
    queryFn: () => listHospitals(),
    staleTime: 5 * 60_000,
  });
}
