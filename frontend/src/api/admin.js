import { request } from './client';

/**
 * @typedef {{
 *   id: string, full_name: string, specialty: string, is_active: boolean,
 *   hospitals: import('./client').Hospital[],
 *   account: { id: string, email: string, is_active: boolean } | null,
 *   appointment_count: number
 * }} AdminDoctor
 */

/** @returns {Promise<AdminDoctor[]>} */
export const listAdminDoctors = () => request('/admin/doctors');

/** @returns {Promise<AdminDoctor>} */
export const getAdminDoctor = (id) => request(`/admin/doctors/${id}`);

/** Body: `{ full_name, specialty, hospital_ids, account?: { email, password } }`. */
export const createDoctor = (body) => request('/admin/doctors', { method: 'POST', body });

/** Body: any of `{ full_name, specialty, hospital_ids, is_active }`. */
export const updateDoctor = (id, body) => request(`/admin/doctors/${id}`, { method: 'PATCH', body });

/** Create the doctor's login, or change its email / reset its password. */
export const setDoctorAccount = (id, body) =>
  request(`/admin/doctors/${id}/account`, { method: 'PUT', body });

export const deleteDoctor = (id) => request(`/admin/doctors/${id}`, { method: 'DELETE' });
