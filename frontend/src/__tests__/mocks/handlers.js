import { http, HttpResponse } from 'msw';

export const API = 'http://localhost:8000/api/v1';

export const adminUser = { id: 'u1', email: 'admin@example.com', role: 'admin', doctor_id: null };

export const hospital = { id: 'h1', name: 'Riverside General' };
export const doctor = { id: 'd1', full_name: 'Dr. Amara Silva', specialty: 'Cardiology', hospitals: [hospital] };

export const makeAppointment = (n = 1, overrides = {}) => ({
  id: `a${n}`,
  patient_name: `Patient ${n}`,
  doctor: { id: doctor.id, full_name: doctor.full_name, specialty: doctor.specialty },
  hospital,
  start_time: '2026-10-15T14:30:00Z',
  appointment_type: 'check_up',
  status: 'scheduled',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  ...overrides,
});

export const emptyPage = () => ({ items: [], total: 0, page: 1, page_size: 20, pages: 0 });

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
  http.get(`${API}/auth/me`, ({ request }) =>
    request.headers.get('Authorization') === 'Bearer test-token'
      ? HttpResponse.json(adminUser)
      : HttpResponse.json(
          { error: { code: 'unauthorized', message: 'Not signed in.' } },
          { status: 401 },
        ),
  ),
  http.get(`${API}/appointments`, () => HttpResponse.json(emptyPage())),
  http.get(`${API}/doctors`, () => HttpResponse.json([doctor])),
  http.get(`${API}/hospitals`, () => HttpResponse.json([hospital])),
];
