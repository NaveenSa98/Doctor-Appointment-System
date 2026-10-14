export const STAFF_ROLES = ['admin', 'doctor'];

/** Where each kind of user lands after signing in. */
export const homeFor = (role) => (role === 'patient' ? '/my-bookings' : '/appointments');
