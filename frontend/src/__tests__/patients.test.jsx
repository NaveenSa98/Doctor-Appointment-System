import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, makeAppointment } from './mocks/handlers';
import { renderApp } from './test-utils';

const location = () => screen.getByTestId('location').textContent;

const patient = (overrides = {}) => ({
  id: 'p1',
  full_name: 'Alice Perera',
  email: 'alice@example.test',
  is_active: true,
  created_at: '2099-01-01T00:00:00Z',
  booking_count: 3,
  last_booking_at: '2099-02-01T09:00:00Z',
  ...overrides,
});

const page = (items, extra = {}) => ({
  items,
  total: items.length,
  page: 1,
  page_size: 20,
  pages: 1,
  ...extra,
});

beforeEach(() => sessionStorage.setItem('am.token', 'test-token'));

describe('patient list', () => {
  it('shows each patient with email and booking numbers', async () => {
    server.use(
      http.get(`${API}/patients`, () =>
        HttpResponse.json(page([patient(), patient({ id: 'p2', full_name: 'Bob Silva', email: 'bob@example.test', booking_count: 0, last_booking_at: null })])),
      ),
    );
    renderApp('/patients');
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row').slice(1);

    expect(rows[0]).toHaveTextContent('Alice Perera');
    expect(rows[0]).toHaveTextContent('alice@example.test');
    expect(rows[0]).toHaveTextContent('3');
    expect(within(rows[0]).getByRole('link', { name: 'Alice Perera' })).toHaveAttribute('href', '/patients/p1');
    expect(rows[1]).toHaveTextContent('–');
    expect(screen.getByText(/Guest bookings are not listed here/)).toBeInTheDocument();
  });

  it('explains the doctor’s narrower view', async () => {
    sessionStorage.setItem('am.token', 'doctor-token');
    renderApp('/patients');
    expect(await screen.findByText(/who have booked with you/)).toBeInTheDocument();
  });

  it('searches with one request after typing stops, and keeps the search in the URL', async () => {
    const queries = [];
    server.use(
      http.get(`${API}/patients`, ({ request }) => {
        queries.push(new URL(request.url).searchParams.get('q'));
        return HttpResponse.json(page([patient()]));
      }),
    );
    const user = userEvent.setup();
    renderApp('/patients');
    await screen.findByText('Alice Perera');

    await user.type(screen.getByRole('searchbox', { name: /Search patients/ }), 'alice');
    await waitFor(() => expect(location()).toBe('/patients?q=alice'));
    await waitFor(() => expect(queries.at(-1)).toBe('alice'));
    expect(queries.filter((q) => q === 'alice')).toHaveLength(1);
  });

  it('restores the search from the URL and shows an empty result', async () => {
    renderApp('/patients?q=nobody');
    expect(await screen.findByText('No patients match your search')).toBeInTheDocument();
    expect(screen.getByRole('searchbox')).toHaveValue('nobody');
  });

  it('shows an empty state when nobody has registered', async () => {
    renderApp('/patients');
    expect(await screen.findByText('No registered patients yet')).toBeInTheDocument();
  });

  it('pages through the list', async () => {
    const pages = [];
    server.use(
      http.get(`${API}/patients`, ({ request }) => {
        const n = Number(new URL(request.url).searchParams.get('page') ?? 1);
        pages.push(n);
        return HttpResponse.json(page([patient({ id: `p${n}`, full_name: `Patient ${n}` })], { page: n, pages: 2, total: 21 }));
      }),
    );
    const user = userEvent.setup();
    renderApp('/patients');
    await screen.findByText('Patient 1');
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('Patient 2');
    expect(location()).toBe('/patients?page=2');
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });
});

describe('who can open the patient pages', () => {
  it('sends a visitor to sign in and a patient to their own bookings', async () => {
    sessionStorage.clear();
    const { unmount } = renderApp('/patients');
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    unmount();

    sessionStorage.setItem('am.token', 'patient-token');
    renderApp('/patients');
    expect(await screen.findByRole('heading', { name: 'My bookings' })).toBeInTheDocument();
  });

  it('shows the menu link to admins and doctors but not patients', async () => {
    const { unmount } = renderApp('/patients');
    expect(await screen.findByRole('link', { name: 'Patients' })).toBeInTheDocument();
    unmount();

    sessionStorage.setItem('am.token', 'doctor-token');
    const second = renderApp('/patients');
    expect(await screen.findByRole('link', { name: 'Patients' })).toBeInTheDocument();
    second.unmount();

    sessionStorage.setItem('am.token', 'patient-token');
    renderApp('/my-bookings');
    await screen.findByRole('heading', { name: 'My bookings' });
    expect(screen.queryByRole('link', { name: 'Patients' })).not.toBeInTheDocument();
  });
});

describe('patient detail', () => {
  it('shows the details and links each booking to its page', async () => {
    server.use(
      http.get(`${API}/patients/p1`, () =>
        HttpResponse.json({ ...patient(), bookings: [makeAppointment(1, { patient_name: 'Alice Perera' }), makeAppointment(2)] }),
      ),
    );
    renderApp('/patients/p1');
    expect(await screen.findByRole('heading', { name: 'Alice Perera' })).toBeInTheDocument();

    const details = screen.getByRole('region', { name: 'Patient details' });
    expect(details).toHaveTextContent('alice@example.test');
    expect(details).toHaveTextContent('Bookings3');

    const bookings = screen.getAllByRole('listitem');
    expect(bookings).toHaveLength(2);
    const link = within(bookings[0]).getByRole('link');
    expect(link).toHaveAttribute('href', '/appointments/a1');
    expect(screen.getByRole('link', { name: 'All patients' })).toHaveAttribute('href', '/patients');
  });

  it('labels the count for a doctor and handles a patient with no bookings', async () => {
    sessionStorage.setItem('am.token', 'doctor-token');
    server.use(
      http.get(`${API}/patients/p1`, () =>
        HttpResponse.json({ ...patient({ booking_count: 0, last_booking_at: null }), bookings: [] }),
      ),
    );
    renderApp('/patients/p1');
    expect(await screen.findByText('Bookings with you')).toBeInTheDocument();
    expect(screen.getByText('No bookings yet')).toBeInTheDocument();
  });

  it('shows an error state for a patient who cannot be found', async () => {
    server.use(
      http.get(`${API}/patients/nope`, () =>
        HttpResponse.json({ error: { code: 'not_found', message: 'Patient not found' } }, { status: 404 }),
      ),
    );
    renderApp('/patients/nope');
    expect(await screen.findByRole('alert')).toHaveTextContent('Patient not found');
  });
});
