import { request } from './client';

/**
 * @typedef {{ on_date: string, reason: string | null }} SkippedDate
 * @typedef {{
 *   id: string, hospital: import('./client').Hospital, weekday: number,
 *   start_time: string, end_time: string, skipped: SkippedDate[]
 * }} DoctorSession
 * @typedef {{ doctor_id: string, utc_offset_minutes: number, sessions: DoctorSession[] }} Schedule
 */

/** Public. `restricted: false` means the doctor has no sessions (use the default hours). */
export const getSlots = (doctorId, params) => request(`/doctors/${doctorId}/slots`, { params });

/** Admin, or the doctor themself. @returns {Promise<Schedule>} */
export const getSchedule = (doctorId) => request(`/doctors/${doctorId}/sessions`);

/** Body: `{ hospital_id, weekday (0 = Monday), start_time: "HH:MM", end_time: "HH:MM" }`. */
export const createSession = (doctorId, body) =>
  request(`/admin/doctors/${doctorId}/sessions`, { method: 'POST', body });

export const updateSession = (sessionId, body) =>
  request(`/admin/sessions/${sessionId}`, { method: 'PATCH', body });

export const deleteSession = (sessionId) => request(`/admin/sessions/${sessionId}`, { method: 'DELETE' });

export const skipDate = (sessionId, body) =>
  request(`/admin/sessions/${sessionId}/skipped-dates`, { method: 'POST', body });

export const restoreDate = (sessionId, day) =>
  request(`/admin/sessions/${sessionId}/skipped-dates/${day}`, { method: 'DELETE' });
