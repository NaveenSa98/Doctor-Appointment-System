import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateAppointment } from '../api/appointments';

/**
 * Change one appointment's status straight from the table.
 * The cached lists update at once; if the API refuses, they are put back.
 */
export function useStatusChange() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }) => updateAppointment(id, { status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: ['appointments'] });
      const snapshots = qc.getQueriesData({ queryKey: ['appointments'] });
      qc.setQueriesData({ queryKey: ['appointments'] }, (page) =>
        page?.items
          ? { ...page, items: page.items.map((a) => (a.id === id ? { ...a, status } : a)) }
          : page,
      );
      return { snapshots };
    },
    onError: (_err, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () =>
      Promise.all(
        ['appointments', 'appointment-stats', 'availability'].map((key) =>
          qc.invalidateQueries({ queryKey: [key] }),
        ),
      ),
  });
}
