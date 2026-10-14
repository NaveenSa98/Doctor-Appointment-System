import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createDoctor,
  deleteDoctor,
  getAdminDoctor,
  listAdminDoctors,
  setDoctorAccount,
  updateDoctor,
} from '../api/admin';

export const useAdminDoctors = () =>
  useQuery({ queryKey: ['admin-doctors'], queryFn: listAdminDoctors });

export const useAdminDoctor = (id) =>
  useQuery({ queryKey: ['admin-doctors', id], queryFn: () => getAdminDoctor(id), enabled: Boolean(id) });

/** Any change here also changes the public doctor list used by the booking form. */
function useRefresh() {
  const qc = useQueryClient();
  return () =>
    Promise.all(['admin-doctors', 'doctors', 'availability'].map((key) => qc.invalidateQueries({ queryKey: [key] })));
}

export function useCreateDoctor() {
  const refresh = useRefresh();
  return useMutation({ mutationFn: createDoctor, onSuccess: refresh });
}

export function useUpdateDoctor(id) {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (body) => updateDoctor(id, body), onSuccess: refresh });
}

export function useSetDoctorAccount(id) {
  const refresh = useRefresh();
  return useMutation({ mutationFn: (body) => setDoctorAccount(id, body), onSuccess: refresh });
}

export function useDeleteDoctor(id) {
  const qc = useQueryClient();
  const refresh = useRefresh();
  return useMutation({
    mutationFn: () => deleteDoctor(id),
    onSuccess: () => {
      qc.removeQueries({ queryKey: ['admin-doctors', id] });
      return refresh();
    },
  });
}
