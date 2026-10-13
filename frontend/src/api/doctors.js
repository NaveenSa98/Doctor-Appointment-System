import { request } from './client';

/** @returns {Promise<import('./client').Hospital[]>} */
export const listHospitals = (params) => request('/hospitals', { params });

/** @returns {Promise<import('./client').Doctor[]>} */
export const listDoctors = (params) => request('/doctors', { params });

/** @returns {Promise<{ doctor_id: string, taken: string[] }>} */
export const getAvailability = (doctorId, params) =>
  request(`/doctors/${doctorId}/availability`, { params });
