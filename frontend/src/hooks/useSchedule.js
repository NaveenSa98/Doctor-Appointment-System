import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createSession,
  deleteSession,
  getSchedule,
  getSlots,
  restoreDate,
  skipDate,
} from '../api/schedule';
import { localDayRange } from '../utils/datetime';

export const useSchedule = (doctorId) =>
  useQuery({ queryKey: ['sessions', doctorId], queryFn: () => getSchedule(doctorId), enabled: Boolean(doctorId) });

/** Bookable times for a doctor at a hospital on a local date. Needs all three to be chosen. */
export function useSlots(doctorId, hospitalId, date) {
  return useQuery({
    queryKey: ['slots', doctorId, hospitalId, date],
    queryFn: () => {
      const { from, to } = localDayRange(date);
      return getSlots(doctorId, { hospital_id: hospitalId, date_from: from, date_to: to });
    },
    enabled: Boolean(doctorId && hospitalId && date),
  });
}

/** Any schedule change alters the booking form's slots and the admin list. */
function useRefresh() {
  const qc = useQueryClient();
  return () =>
    Promise.all(['sessions', 'slots', 'availability'].map((key) => qc.invalidateQueries({ queryKey: [key] })));
}

export function useCreateSession(doctorId) {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (body) => createSession(doctorId, body), onSuccess: refresh });
}

export function useDeleteSession() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: deleteSession, onSuccess: refresh });
}

export function useSkipDate() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: ({ id, ...body }) => skipDate(id, body), onSuccess: refresh });
}

export function useRestoreDate() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: ({ id, day }) => restoreDate(id, day), onSuccess: refresh });
}
