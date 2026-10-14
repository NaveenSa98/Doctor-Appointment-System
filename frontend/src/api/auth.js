import { request } from './client';

/** @returns {Promise<{ access_token: string, user: import('./client').User }>} */
export const login = (email, password) =>
  request('/auth/login', { method: 'POST', body: { email, password } });

/** @returns {Promise<import('./client').User>} */
export const getMe = () => request('/auth/me');

/** Create a patient account; the response signs the new user in. */
export const register = (fullName, email, password) =>
  request('/auth/register', { method: 'POST', body: { full_name: fullName, email, password } });

/** Change name, email or password. Email and password changes need `current_password`. */
export const updateProfile = (body) => request('/auth/me', { method: 'PATCH', body });

/** Delete the signed-in patient's own account. Past bookings are kept. */
export const deleteAccount = (password) => request('/auth/me', { method: 'DELETE', body: { password } });
