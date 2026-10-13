/**
 * @typedef {{ id: string, email: string, role: 'admin'|'doctor', doctor_id: string|null }} User
 * @typedef {{ id: string, name: string }} Hospital
 * @typedef {{ id: string, full_name: string, specialty: string, hospitals: Hospital[] }} Doctor
 * @typedef {'scheduled'|'confirmed'|'completed'|'cancelled'|'no_show'} AppointmentStatus
 * @typedef {{
 *   id: string, patient_name: string,
 *   doctor: { id: string, full_name: string, specialty: string },
 *   hospital: Hospital, start_time: string, appointment_type: string,
 *   status: AppointmentStatus, created_at: string, updated_at: string
 * }} Appointment
 */

const BASE = import.meta.env.VITE_API_URL ?? '/api/v1';
const TOKEN_KEY = 'am.token';

/** Error carrying the backend's `{ error: { code, message, details? } }` shape. */
export class ApiError extends Error {
  /**
   * @param {number} status HTTP status (0 for a network failure)
   * @param {string} code machine-readable error code
   * @param {string} message human-readable message
   * @param {unknown} [details] field errors, only present on 422
   */
  constructor(status, code, message, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let unauthorizedHandler = null;

/** Register the callback fired when an authenticated request gets a 401. */
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
}

/** @returns {string|null} the stored JWT, if any. */
export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Store (or clear, with null) the JWT for this browser tab. */
export function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the session just won't survive a reload */
  }
}

function buildUrl(path, params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    for (const v of Array.isArray(value) ? value : [value]) {
      if (v !== undefined && v !== null && v !== '') query.append(key, String(v));
    }
  }
  const qs = query.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ''}`;
}

/**
 * Thin fetch wrapper: attaches the token, parses the error shape, and
 * signs the user out on a 401 for an authenticated request.
 * @param {string} path path under the API base, e.g. `/doctors`
 * @param {{ method?: string, body?: unknown, params?: Record<string, unknown> }} [options]
 */
export async function request(path, { method = 'GET', body, params } = {}) {
  const token = getToken();
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach the server.');
  }

  if (res.status === 204) return null;
  const payload = await res.json().catch(() => null);

  if (!res.ok) {
    if (res.status === 401 && token) {
      setToken(null);
      unauthorizedHandler?.();
    }
    const err = payload?.error;
    throw new ApiError(
      res.status,
      err?.code ?? 'http_error',
      err?.message ?? `Request failed (${res.status}).`,
      err?.details,
    );
  }
  return payload;
}
