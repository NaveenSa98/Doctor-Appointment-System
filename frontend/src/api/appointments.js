import { request } from './client';

/** Public: works without a token. @returns {Promise<import('./client').Appointment>} */
export const createAppointment = (body) => request('/appointments', { method: 'POST', body });

export const listAppointments = (params) => request('/appointments', { params });

export const getAppointment = (id) => request(`/appointments/${id}`);

export const updateAppointment = (id, body) =>
  request(`/appointments/${id}`, { method: 'PATCH', body });

export const deleteAppointment = (id) => request(`/appointments/${id}`, { method: 'DELETE' });

export const getStats = (params) => request('/appointments/stats', { params });
