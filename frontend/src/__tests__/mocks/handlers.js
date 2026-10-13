import { http, HttpResponse } from 'msw';

export const API = 'http://localhost:8000/api/v1';

export const adminUser = { id: 'u1', email: 'admin@example.com', role: 'admin', doctor_id: null };
export const doctorUser = { id: 'u2', email: 'doc@example.com', role: 'doctor', doctor_id: 'd1' };

export const hospital = { id: 'h1', name: 'Riverside General' };
export const hospital2 = { id: 'h2', name: "St. Mary's Clinic" };
// d1 visits both hospitals; d2 only visits h2.
export const doctor = {
  id: 'd1',
  full_name: 'Dr. Amara Silva',
  specialty: 'Cardiology',
  hospitals: [hospital, hospital2],
};
export const doctor2 = { id: 'd2', full_name: 'Dr. Ravi Menon', specialty: 'Dermatology', hospitals: [hospital2] };

export const makeAppointment = (n = 1, overrides = {}) => ({
  id: `a${n}`,
  patient_name: `Patient ${n}`,
  doctor: { id: doctor.id, full_name: doctor.full_name, specialty: doctor.specialty },
  hospital,
  start_time: '2099-01-05T15:00:00Z',
  appointment_type: 'check_up',
  status: 'scheduled',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...overrides,
});

export const emptyPage = () => ({ items: [], total: 0, page: 1, page_size: 20, pages: 0 });

const unauthorized = () =>
  HttpResponse.json({ error: { code: 'unauthorized', message: 'Not signed in.' } }, { status: 401 });

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    const { email, password } = await request.json();
    if (email === adminUser.email && password === 'correct-password') {
      return HttpResponse.json({
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: adminUser,
      });
    }
    return HttpResponse.json(
      { error: { code: 'invalid_credentials', message: 'Incorrect email or password.' } },
      { status: 401 },
    );
  }),
  http.get(`${API}/auth/me`, ({ request }) => {
    const auth = request.headers.get('Authorization');
    if (auth === 'Bearer test-token') return HttpResponse.json(adminUser);
    if (auth === 'Bearer doctor-token') return HttpResponse.json(doctorUser);
    return unauthorized();
  }),
  http.get(`${API}/appointments`, () => HttpResponse.json(emptyPage())),
  http.get(`${API}/doctors`, () => HttpResponse.json([doctor, doctor2])),
  http.get(`${API}/hospitals`, () => HttpResponse.json([hospital, hospital2])),
  http.get(`${API}/doctors/:id/availability`, ({ params }) =>
    HttpResponse.json({ doctor_id: params.id, taken: [] }),
  ),
  http.post(`${API}/appointments`, async ({ request }) => {
    const body = await request.json();
    const created = makeAppointment(99, {
      patient_name: body.patient_name,
      start_time: body.start_time,
      appointment_type: body.appointment_type,
    });
    return HttpResponse.json(created, { status: 201 });
  }),
];
