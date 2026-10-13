import { request } from './client';

/** @returns {Promise<{ access_token: string, user: import('./client').User }>} */
export const login = (email, password) =>
  request('/auth/login', { method: 'POST', body: { email, password } });

/** @returns {Promise<import('./client').User>} */
export const getMe = () => request('/auth/me');
