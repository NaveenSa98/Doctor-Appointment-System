import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, makeAppointment, patientUser } from './mocks/handlers';
import { renderApp } from './test-utils';
import { splitBookings } from '../pages/MyBookingsPage';

const location = () => screen.getByTestId('location').textContent;
const asPatient = () => sessionStorage.setItem('am.token', 'patient-token');

async function fillSignUp(user, { name = 'Pat Patient', email = 'pat@example.com', password = 'long-enough-1', confirm } = {}) {
  await user.type(screen.getByLabelText('Full name'), name);
  await user.type(screen.getByLabelText('Email'), email);
  await user.type(screen.getByLabelText('Password'), password);
  await user.type(screen.getByLabelText('Confirm password'), confirm ?? password);
}

describe('sign up', () => {
  it('creates a patient account, signs them in and lands on My bookings', async () => {
    let body;
    server.use(
      http.post(`${API}/auth/register`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          { access_token: 'patient-token', token_type: 'bearer', expires_in: 1800, user: patientUser },
          { status: 201 },
        );
      }),
    );
    const user = userEvent.setup();
    renderApp('/signup');
    await fillSignUp(user);
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('heading', { name: 'My bookings' })).toBeInTheDocument();
    expect(body).toEqual({ full_name: 'Pat Patient', email: 'pat@example.com', password: 'long-enough-1' });
    expect(sessionStorage.getItem('am.token')).toBe('patient-token');
    expect(location()).toBe('/my-bookings');
  });

  it('checks the form before sending anything', async () => {
    const user = userEvent.setup();
    renderApp('/signup');
    await fillSignUp(user, { name: 'P', email: 'nope', password: 'short', confirm: 'different' });
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText(/at least 2 characters/)).toBeInTheDocument();
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Use at least 8 characters.')).toBeInTheDocument();
    expect(screen.getByText('The passwords do not match.')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows a taken email on the email field', async () => {
    server.use(
      http.post(`${API}/auth/register`, () =>
        HttpResponse.json({ error: { code: 'email_taken', message: 'taken' } }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/signup');
    await fillSignUp(user);
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText(/already exists/)).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled();
  });

  it('is linked from the sign-in page and the header', async () => {
    const user = userEvent.setup();
    renderApp('/login');
    await user.click(screen.getByRole('link', { name: 'Create an account' }));
    expect(await screen.findByRole('heading', { name: 'Create your account' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign up' })).toBeInTheDocument();
  });
});

describe('role-aware pages', () => {
  it('keeps patients out of the staff pages and staff out of My bookings', async () => {
    asPatient();
    const { unmount } = renderApp('/appointments');
    expect(await screen.findByRole('heading', { name: 'My bookings' })).toBeInTheDocument();
    expect(location()).toBe('/my-bookings');
    unmount();

    sessionStorage.setItem('am.token', 'test-token');
    renderApp('/my-bookings');
    expect(await screen.findByRole('heading', { name: 'Appointments' })).toBeInTheDocument();
    expect(location()).toBe('/appointments');
  });

  it('sends a visitor who is not signed in to the sign-in page', async () => {
    renderApp('/my-bookings');
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('shows a patient the patient menu only', async () => {
    asPatient();
    renderApp('/my-bookings');
    const nav = await screen.findByRole('navigation', { name: 'Main' });
    expect(within(nav).getByRole('link', { name: 'My bookings' })).toBeInTheDocument();
    expect(within(nav).queryByRole('link', { name: 'Appointments' })).not.toBeInTheDocument();
  });

  it('pre-fills the booking form with the patient name', async () => {
    asPatient();
    renderApp('/book');
    expect(await screen.findByLabelText('Patient name')).toHaveValue('Pat Patient');
  });
});

describe('my bookings', () => {
  it('splits upcoming from past and cancelled', () => {
    const now = Date.parse('2099-01-05T12:00:00Z');
    const future = makeAppointment(1, { start_time: '2099-01-06T09:00:00Z' });
    const later = makeAppointment(2, { start_time: '2099-01-09T09:00:00Z' });
    const past = makeAppointment(3, { start_time: '2099-01-01T09:00:00Z', status: 'completed' });
    const cancelled = makeAppointment(4, { start_time: '2099-01-08T09:00:00Z', status: 'cancelled' });

    const { upcoming, past: rest } = splitBookings([later, past, cancelled, future], now);
    expect(upcoming.map((a) => a.id)).toEqual(['a1', 'a2']);
    expect(rest.map((a) => a.id)).toEqual(['a4', 'a3']);
  });

  it('lists the bookings, or invites the patient to make one', async () => {
    asPatient();
    server.use(
      http.get(`${API}/appointments`, () =>
        HttpResponse.json({
          items: [makeAppointment(1, { patient_name: 'Pat Patient' })],
          total: 1,
          page: 1,
          page_size: 100,
          pages: 1,
        }),
      ),
    );
    const { unmount } = renderApp('/my-bookings');
    expect(await screen.findByRole('region', { name: 'Upcoming' })).toHaveTextContent('Dr. Amara Silva');
    unmount();

    server.resetHandlers();
    renderApp('/my-bookings');
    expect(await screen.findByText('No bookings yet')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Book an appointment' }).length).toBeGreaterThan(0);
  });
});

describe('account settings', () => {
  it('saves a new name', async () => {
    asPatient();
    let body;
    server.use(
      http.patch(`${API}/auth/me`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...patientUser, ...body });
      }),
    );
    const user = userEvent.setup();
    renderApp('/account');
    const name = await screen.findByLabelText('Full name');
    await user.clear(name);
    await user.type(name, 'Patricia P');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(body).toEqual({ full_name: 'Patricia P' });
  });

  it('asks for the current password when changing it, and shows the server message', async () => {
    asPatient();
    server.use(
      http.patch(`${API}/auth/me`, () =>
        HttpResponse.json(
          {
            error: {
              code: 'validation_error',
              message: 'Request validation failed',
              details: [{ field: 'current_password', message: 'is incorrect' }],
            },
          },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp('/account');
    await user.type(await screen.findByLabelText('New password'), 'another-long-one');
    await user.type(screen.getByLabelText('Current password', { selector: '#old-password' }), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Change password' }));

    expect(await screen.findByText('Your password is incorrect.')).toBeInTheDocument();
    // The session survives: a 422, not a 401.
    expect(sessionStorage.getItem('am.token')).toBe('patient-token');
  });

  it('deletes the account only after confirming with the password, then signs out', async () => {
    asPatient();
    let deletes = 0;
    let body;
    server.use(
      http.delete(`${API}/auth/me`, async ({ request }) => {
        deletes += 1;
        body = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/account');
    await user.click(await screen.findByRole('button', { name: 'Delete my account' }));

    const dialog = screen.getByRole('dialog', { name: 'Delete your account?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(deletes).toBe(0);

    await user.click(screen.getByRole('button', { name: 'Delete my account' }));
    const again = screen.getByRole('dialog');
    await user.type(within(again).getByLabelText('Password'), 'long-enough-1');
    await user.click(within(again).getByRole('button', { name: 'Delete account' }));

    await waitFor(() => expect(location()).toBe('/'));
    expect(body).toEqual({ password: 'long-enough-1' });
    expect(sessionStorage.getItem('am.token')).toBeNull();
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('does not offer account deletion to staff', async () => {
    sessionStorage.setItem('am.token', 'test-token');
    renderApp('/account');
    expect(await screen.findByText(/ask an administrator/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete my account' })).not.toBeInTheDocument();
  });
});
