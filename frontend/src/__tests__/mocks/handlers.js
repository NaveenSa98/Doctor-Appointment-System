import { http, HttpResponse } from 'msw';

export const API = 'http://localhost:8000/api/v1';

export const adminUser = { id: 'u1', email: 'admin@example.com', role: 'admin', doctor_id: null };

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
];
