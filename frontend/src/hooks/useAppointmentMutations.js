import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createAppointment, deleteAppointment, updateAppointment } from '../api/appointments';

/** After any change, the list and slot availability are stale. */
function useInvalidate() {
  const qc = useQueryClient();
  return () =>
    Promise.all(['appointments', 'appointment-stats', 'availability'].map((key) => qc.invalidateQueries({ queryKey: [key] })));
}

export function useCreateAppointment() {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: createAppointment, onSuccess: invalidate });
}

export function useUpdateAppointment(id) {
  const qc = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body) => updateAppointment(id, body),
    onSuccess: (updated) => {
      qc.setQueryData(['appointment', id], updated);
      return invalidate();
    },
  });
}

export function useDeleteAppointment(id) {
  const qc = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: () => deleteAppointment(id),
    onSuccess: () => {
      qc.removeQueries({ queryKey: ['appointment', id] });
      return invalidate();
    },
  });
}
