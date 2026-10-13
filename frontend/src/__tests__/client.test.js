import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API } from './mocks/handlers';
import { ApiError, getToken, request, setToken, setUnauthorizedHandler } from '../api/client';

describe('api client', () => {
  it('maps the backend error shape to ApiError', async () => {
    server.use(
      http.get(`${API}/doctors`, () =>
        HttpResponse.json(
          { error: { code: 'validation_error', message: 'Bad input', details: [{ field: 'x' }] } },
          { status: 422 },
        ),
      ),
    );
    const err = await request('/doctors').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 422, code: 'validation_error', message: 'Bad input' });
    expect(err.details).toEqual([{ field: 'x' }]);
  });

  it('clears the session and notifies on a 401 for an authenticated request', async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    setToken('stale-token');
    await expect(request('/auth/me')).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledOnce();
    setUnauthorizedHandler(null);
  });

  it('attaches the bearer token and repeats array params', async () => {
    let seen;
    server.use(
      http.get(`${API}/appointments`, ({ request: req }) => {
        seen = { auth: req.headers.get('Authorization'), url: new URL(req.url) };
        return HttpResponse.json([]);
      }),
    );
    setToken('abc');
    await request('/appointments', { params: { status: ['scheduled', 'confirmed'], q: '' } });
    expect(seen.auth).toBe('Bearer abc');
    expect(seen.url.searchParams.getAll('status')).toEqual(['scheduled', 'confirmed']);
    expect(seen.url.searchParams.has('q')).toBe(false);
  });
});
