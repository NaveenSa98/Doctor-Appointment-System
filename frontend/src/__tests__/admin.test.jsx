import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, hospital } from './mocks/handlers';
import { renderApp } from './test-utils';

const location = () => screen.getByTestId('location').textContent;

const adminDoctor = (overrides = {}) => ({
  id: 'd1',
  full_name: 'Dr. Amara Silva',
  specialty: 'Cardiology',
  is_active: true,
  hospitals: [hospital],
  account: { id: 'u9', email: 'amara@clinic.test', is_active: true },
  appointment_count: 3,
  ...overrides,
});

beforeEach(() => sessionStorage.setItem('am.token', 'test-token'));

describe('admin doctor list', () => {
  it('shows each doctor with login, hospitals, bookings and status', async () => {
    server.use(
      http.get(`${API}/admin/doctors`, () =>
        HttpResponse.json([
          adminDoctor(),
          adminDoctor({ id: 'd2', full_name: 'Dr. Ravi Menon', account: null, is_active: false, appointment_count: 0 }),
        ]),
      ),
    );
    renderApp('/admin/doctors');
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);

    expect(rows[0]).toHaveTextContent('Dr. Amara Silva');
    expect(rows[0]).toHaveTextContent('amara@clinic.test');
    expect(rows[0]).toHaveTextContent('Riverside General');
    expect(rows[0]).toHaveTextContent('Active');
    expect(rows[1]).toHaveTextContent('No login yet');
    expect(rows[1]).toHaveTextContent('Inactive');
  });

  it('is for admins only', async () => {
    sessionStorage.setItem('am.token', 'doctor-token');
    const { unmount } = renderApp('/admin/doctors');
    expect(await screen.findByRole('heading', { name: 'Appointments' })).toBeInTheDocument();
    expect(location()).toBe('/appointments');
    expect(screen.queryByRole('link', { name: 'Doctors' })).not.toBeInTheDocument();
    unmount();

    sessionStorage.setItem('am.token', 'patient-token');
    renderApp('/admin/doctors');
    expect(await screen.findByRole('heading', { name: 'My bookings' })).toBeInTheDocument();
  });

  it('has an Add doctor button and a Doctors menu link for the admin', async () => {
    renderApp('/admin/doctors');
    expect(await screen.findByText('No doctors yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Doctors' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Add doctor' })).toBeInTheDocument();
  });
});

async function fillNewDoctor(user, { login = true } = {}) {
  await user.type(await screen.findByLabelText('Full name'), 'Dr. Nadia Perera');
  await user.type(screen.getByLabelText('Specialty'), 'Neurology');
  await user.click(screen.getByRole('checkbox', { name: 'Riverside General' }));
  if (login) {
    await user.type(screen.getByLabelText('Login email'), 'nadia@clinic.test');
    await user.type(screen.getByLabelText('Initial password'), 'initial-pass-1');
  }
}

describe('add a doctor', () => {
  it('checks the form before sending anything', async () => {
    const user = userEvent.setup();
    renderApp('/admin/doctors/new');
    await user.click(await screen.findByRole('button', { name: 'Add doctor' }));

    expect(await screen.findByText('Enter the doctor’s full name.')).toBeInTheDocument();
    expect(screen.getByText('Enter a specialty.')).toBeInTheDocument();
    expect(screen.getByText('Choose at least one hospital.')).toBeInTheDocument();
    expect(screen.getByText('Enter a valid email address.')).toBeInTheDocument();
    expect(screen.getByText('Use at least 8 characters.')).toBeInTheDocument();
  });

  it('creates the doctor with a login and opens their page', async () => {
    let body;
    server.use(
      http.post(`${API}/admin/doctors`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(adminDoctor({ id: 'd7' }), { status: 201 });
      }),
      http.get(`${API}/admin/doctors/d7`, () => HttpResponse.json(adminDoctor({ id: 'd7' }))),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/new');
    await fillNewDoctor(user);
    await user.click(screen.getByRole('button', { name: 'Add doctor' }));

    await waitFor(() => expect(location()).toBe('/admin/doctors/d7'));
    expect(body).toEqual({
      full_name: 'Dr. Nadia Perera',
      specialty: 'Neurology',
      hospital_ids: ['h1'],
      account: { email: 'nadia@clinic.test', password: 'initial-pass-1' },
    });
  });

  it('can skip the login', async () => {
    let body;
    server.use(
      http.post(`${API}/admin/doctors`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(adminDoctor({ id: 'd8', account: null }), { status: 201 });
      }),
      http.get(`${API}/admin/doctors/d8`, () => HttpResponse.json(adminDoctor({ id: 'd8', account: null }))),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/new');
    await screen.findByLabelText('Full name');
    await user.click(screen.getByRole('checkbox', { name: 'Create a login for this doctor now' }));
    await fillNewDoctor(user, { login: false });
    await user.click(screen.getByRole('button', { name: 'Add doctor' }));

    await waitFor(() => expect(location()).toBe('/admin/doctors/d8'));
    expect(body).not.toHaveProperty('account');
  });

  it('shows a taken login email on the email field', async () => {
    server.use(
      http.post(`${API}/admin/doctors`, () =>
        HttpResponse.json({ error: { code: 'email_taken', message: 'taken' } }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/new');
    await fillNewDoctor(user);
    await user.click(screen.getByRole('button', { name: 'Add doctor' }));

    expect(await screen.findByText('Another account already uses this email.')).toBeInTheDocument();
    expect(screen.getByLabelText('Login email')).toHaveAttribute('aria-invalid', 'true');
    expect(location()).toBe('/admin/doctors/new');
  });
});

describe('edit a doctor', () => {
  beforeEach(() => {
    server.use(http.get(`${API}/admin/doctors/d1`, () => HttpResponse.json(adminDoctor())));
  });

  it('pre-fills the form and saves changes', async () => {
    let body;
    server.use(
      http.patch(`${API}/admin/doctors/d1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(adminDoctor(body));
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    const specialty = await screen.findByLabelText('Specialty');
    expect(specialty).toHaveValue('Cardiology');
    expect(screen.getByRole('checkbox', { name: 'Riverside General' })).toBeChecked();

    await user.clear(specialty);
    await user.type(specialty, 'Neurology');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(await screen.findByText('Saved.')).toBeInTheDocument();
    expect(body).toEqual({ full_name: 'Dr. Amara Silva', specialty: 'Neurology', hospital_ids: ['h1'] });
  });

  it('deactivates a doctor', async () => {
    let body;
    server.use(
      http.patch(`${API}/admin/doctors/d1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(adminDoctor(body));
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await user.click(await screen.findByRole('button', { name: 'Deactivate doctor' }));
    await waitFor(() => expect(body).toEqual({ is_active: false }));
  });

  it('resets the password', async () => {
    let body;
    server.use(
      http.put(`${API}/admin/doctors/d1/account`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(adminDoctor());
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await user.type(await screen.findByLabelText('New password'), 'a-new-password-1');
    await user.click(screen.getByRole('button', { name: 'Update login' }));

    expect(await screen.findByText('Login updated.')).toBeInTheDocument();
    expect(body).toEqual({ password: 'a-new-password-1' });
  });

  it('asks before deleting and explains when the doctor has appointments', async () => {
    let deletes = 0;
    server.use(
      http.delete(`${API}/admin/doctors/d1`, () => {
        deletes += 1;
        return HttpResponse.json(
          { error: { code: 'doctor_has_appointments', message: 'has appointments' } },
          { status: 409 },
        );
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await user.click(await screen.findByRole('button', { name: 'Delete doctor' }));
    const dialog = screen.getByRole('dialog', { name: 'Delete Dr. Amara Silva?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(deletes).toBe(0);

    await user.click(screen.getByRole('button', { name: 'Delete doctor' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete doctor' }));
    expect(await screen.findByText(/cannot be deleted\. Deactivate them instead/)).toBeInTheDocument();
    expect(deletes).toBe(1);
    expect(location()).toBe('/admin/doctors/d1');
  });

  it('deletes a doctor with no appointments and returns to the list', async () => {
    server.use(http.delete(`${API}/admin/doctors/d1`, () => new HttpResponse(null, { status: 204 })));
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await user.click(await screen.findByRole('button', { name: 'Delete doctor' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete doctor' }));

    await waitFor(() => expect(location()).toBe('/admin/doctors'));
  });
});
