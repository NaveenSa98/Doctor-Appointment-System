import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, doctor, hospital, makeAppointment } from './mocks/handlers';
import { renderApp } from './test-utils';
import { localToUtcIso } from '../utils/datetime';

const DATE = '2099-01-05';

/** Fill every field of the booking form and leave the submit button for the test. */
async function fillBooking(user, { name = 'Jane Perera', slot = '10:00' } = {}) {
  await user.selectOptions(await screen.findByLabelText('Hospital'), 'h1');
  await user.selectOptions(screen.getByLabelText('Doctor'), 'd1');
  fireEvent.change(screen.getByLabelText('Date'), { target: { value: DATE } });
  await user.click(await screen.findByRole('button', { name: new RegExp(`^${slot}`) }));
  await user.type(screen.getByLabelText('Patient name'), name);
}

const submit = (user) => user.click(screen.getByRole('button', { name: 'Book appointment' }));
const optionNames = (select) => within(select).getAllByRole('option').map((o) => o.textContent);
const location = () => screen.getByTestId('location').textContent;

describe('booking form', () => {
  it('shows client-side validation messages', async () => {
    const user = userEvent.setup();
    renderApp('/book');
    await screen.findByLabelText('Hospital');
    await submit(user);

    expect(await screen.findByText('Choose a hospital.')).toBeInTheDocument();
    expect(screen.getByText('Choose a doctor.')).toBeInTheDocument();
    expect(screen.getByText('Choose a date.')).toBeInTheDocument();
    expect(screen.getByText('Choose a time.')).toBeInTheDocument();
    expect(screen.getByText('Enter at least 2 characters.')).toBeInTheDocument();
    expect(screen.getByLabelText('Hospital')).toHaveAttribute('aria-invalid', 'true');
  });

  it('lets an anonymous visitor book without a token and shows the reference id', async () => {
    let seen;
    server.use(
      http.post(`${API}/appointments`, async ({ request }) => {
        seen = { auth: request.headers.get('Authorization'), body: await request.json() };
        return HttpResponse.json(makeAppointment(99, { patient_name: 'Jane Perera' }), { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/book');
    await fillBooking(user);
    await submit(user);

    expect(await screen.findByRole('heading', { name: 'You are booked' })).toBeInTheDocument();
    expect(screen.getByLabelText('Reference number')).toHaveTextContent('a99');
    expect(seen.auth).toBeNull();
    expect(seen.body).toEqual({
      patient_name: 'Jane Perera',
      doctor_id: 'd1',
      hospital_id: 'h1',
      start_time: localToUtcIso(`${DATE}T10:00`),
      appointment_type: 'consultation',
    });
  });

  it('only lists doctors of the chosen hospital', async () => {
    const user = userEvent.setup();
    renderApp('/book');
    const hospitalSelect = await screen.findByLabelText('Hospital');
    const doctorSelect = screen.getByLabelText('Doctor');
    expect(optionNames(doctorSelect)).toHaveLength(3); // placeholder + both doctors

    await user.selectOptions(hospitalSelect, 'h1');
    expect(optionNames(doctorSelect)).toEqual(['Select a doctor', 'Dr. Amara Silva, Cardiology']);
    await user.selectOptions(hospitalSelect, 'h2');
    expect(optionNames(doctorSelect)).toHaveLength(3);
  });

  it('disables taken slots', async () => {
    server.use(
      http.get(`${API}/doctors/d1/availability`, () =>
        HttpResponse.json({ doctor_id: 'd1', taken: [localToUtcIso(`${DATE}T10:00`)] }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/book');
    await user.selectOptions(await screen.findByLabelText('Doctor'), 'd1');
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: DATE } });

    await waitFor(() => expect(screen.getByRole('button', { name: /^10:00/ })).toBeDisabled());
    expect(screen.getByRole('button', { name: /^10:30/ })).toBeEnabled();
  });

  it('pre-selects a signed-in doctor and offers only their hospitals', async () => {
    sessionStorage.setItem('am.token', 'doctor-token');
    server.use(
      http.get(`${API}/doctors`, () =>
        HttpResponse.json([{ ...doctor, hospitals: [hospital] }]),
      ),
    );
    renderApp('/book');
    const doctorSelect = await screen.findByLabelText('Doctor');
    expect(doctorSelect).toHaveValue('d1');
    expect(optionNames(doctorSelect)).toEqual(['Select a doctor', 'Dr. Amara Silva, Cardiology']);
    expect(optionNames(screen.getByLabelText('Hospital'))).toEqual(['Select a hospital', 'Riverside General']);
  });
});

describe('booking errors', () => {
  const failWith = (status, error) =>
    server.use(http.post(`${API}/appointments`, () => HttpResponse.json({ error }, { status })));

  it('puts a 409 on the time field', async () => {
    failWith(409, { code: 'conflict', message: 'Slot taken' });
    const user = userEvent.setup();
    renderApp('/book');
    await fillBooking(user);
    await submit(user);

    expect(await screen.findByText(/no longer available/i)).toBeInTheDocument();
    expect(location()).toBe('/book');
  });

  it('maps a 422 details entry to its field', async () => {
    failWith(422, {
      code: 'validation_error',
      message: 'Request validation failed',
      details: [{ field: 'patient_name', message: 'Name has invalid characters' }],
    });
    const user = userEvent.setup();
    renderApp('/book');
    await fillBooking(user);
    await submit(user);

    expect(await screen.findByText('Name has invalid characters')).toBeInTheDocument();
    expect(screen.getByLabelText('Patient name')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows a friendly message on 429', async () => {
    failWith(429, { code: 'rate_limited', message: 'slow down' });
    const user = userEvent.setup();
    renderApp('/book');
    await fillBooking(user);
    await submit(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts, try again shortly.');
  });

  it('disables submit while pending so a double click sends one request', async () => {
    let posts = 0;
    server.use(
      http.post(`${API}/appointments`, async () => {
        posts += 1;
        await delay(150);
        return HttpResponse.json(makeAppointment(99), { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/book');
    await fillBooking(user);
    const button = screen.getByRole('button', { name: 'Book appointment' });
    await user.dblClick(button);

    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
    await screen.findByRole('heading', { name: 'You are booked' });
    expect(posts).toBe(1);
  });
});

describe('edit and delete', () => {
  const existing = () =>
    makeAppointment(1, { patient_name: 'Jane Perera', start_time: localToUtcIso(`${DATE}T10:00`) });

  beforeEach(() => {
    sessionStorage.setItem('am.token', 'test-token');
    server.use(http.get(`${API}/appointments/a1`, () => HttpResponse.json(existing())));
  });

  it('pre-fills the form in local time and patches only what changed', async () => {
    let patch;
    server.use(
      http.patch(`${API}/appointments/a1`, async ({ request }) => {
        patch = await request.json();
        return HttpResponse.json({ ...existing(), ...patch });
      }),
    );
    const user = userEvent.setup();
    renderApp('/appointments/a1');

    expect(await screen.findByLabelText('Date')).toHaveValue(DATE);
    expect(screen.getByLabelText('Patient name')).toHaveValue('Jane Perera');
    expect(screen.getByRole('button', { name: /^10:00/ })).toHaveAttribute('aria-pressed', 'true');

    await user.clear(screen.getByLabelText('Patient name'));
    await user.type(screen.getByLabelText('Patient name'), 'Jane P');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(location()).toBe('/appointments'));
    expect(patch).toEqual({ patient_name: 'Jane P' });
  });

  it('deletes only after confirmation and returns focus when cancelled', async () => {
    let deletes = 0;
    server.use(
      http.delete(`${API}/appointments/a1`, () => {
        deletes += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/appointments/a1');
    const open = await screen.findByRole('button', { name: 'Delete' });

    await user.click(open);
    const dialog = screen.getByRole('dialog', { name: 'Delete this appointment?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(open).toHaveFocus();
    expect(deletes).toBe(0);

    await user.click(open);
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(location()).toBe('/appointments'));
    expect(deletes).toBe(1);
  });
});
