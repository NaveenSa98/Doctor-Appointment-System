import { request } from './client';

/**
 * @typedef {{
 *   id: string, full_name: string | null, email: string, is_active: boolean,
 *   created_at: string, booking_count: number, last_booking_at: string | null
 * }} Patient
 */

/** Staff only. Params: `q`, `page`, `page_size`. @returns {Promise<{ items: Patient[] }>} */
export const listPatients = (params) => request('/patients', { params });

/** @returns {Promise<Patient & { bookings: import('./client').Appointment[] }>} */
export const getPatient = (id) => request(`/patients/${id}`);
