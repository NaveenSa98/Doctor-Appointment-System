import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, doctor, doctor2, hospital, makeAppointment, makeStats } from './mocks/handlers';
import { renderApp } from './test-utils';
import { localToUtcIso } from '../utils/datetime';

beforeEach(() => sessionStorage.setItem('am.token', 'test-token'));

const onePage = (items) => ({ items, total: items.length, page: 1, page_size: 20, pages: 1 });

describe('status quick-change', () => {
  it('sends a PATCH and shows the new status before the server answers', async () => {
    let status = 'scheduled';
    let responded = false;
    let body;
    server.use(
      http.get(`${API}/appointments`, () => HttpResponse.json(onePage([makeAppointment(1, { status })]))),
      http.patch(`${API}/appointments/a1`, async ({ request }) => {
        body = await request.json();
        await delay(300);
        status = body.status;
        responded = true;
        return HttpResponse.json(makeAppointment(1, { status }));
      }),
    );
    const user = userEvent.setup();
    renderApp('/appointments');
    const select = await screen.findByRole('combobox', { name: 'Status for Patient 1' });

    await user.selectOptions(select, 'confirmed');
    await waitFor(() => expect(select).toHaveValue('confirmed'));
    expect(responded).toBe(false); // optimistic: the UI moved first

    await waitFor(() => expect(responded).toBe(true));
    expect(body).toEqual({ status: 'confirmed' });
    await waitFor(() => expect(select).toHaveValue('confirmed'));
  });

  it('rolls back and shows an error when the API refuses', async () => {
    server.use(
      http.get(`${API}/appointments`, () => HttpResponse.json(onePage([makeAppointment(1)]))),
      http.patch(`${API}/appointments/a1`, async () => {
        await delay(100);
        return HttpResponse.json({ error: { code: 'server_error', message: 'boom' } }, { status: 500 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/appointments');
    const select = await screen.findByRole('combobox', { name: 'Status for Patient 1' });

    await user.selectOptions(select, 'cancelled');
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i);
    expect(select).toHaveValue('scheduled');
  });
});

describe('count tiles', () => {
  it('shows the totals and passes the doctor filter to the stats request', async () => {
    const requests = [];
    server.use(
      http.get(`${API}/appointments/stats`, ({ request }) => {
        requests.push(new URL(request.url));
        return HttpResponse.json(makeStats({ scheduled: 5, confirmed: 3, cancelled: 1 }));
      }),
    );
    renderApp('/appointments?doctor_id=d1');
    const tiles = await screen.findByLabelText('Appointment counts');

    await waitFor(() => expect(within(tiles).getByText('Total').closest('div')).toHaveTextContent('Total9'));
    expect(within(tiles).getByText('Scheduled').closest('div')).toHaveTextContent('Scheduled5');
    expect(within(tiles).getByText('No show').closest('div')).toHaveTextContent('No show0');
    expect(requests.at(-1).searchParams.get('doctor_id')).toBe('d1');
  });
});

describe('day view', () => {
  const DATE = '2099-01-05';
  const at = (time) => localToUtcIso(`${DATE}T${time}`);
  const row = (n, doc, time) =>
    makeAppointment(n, {
      doctor: { id: doc.id, full_name: doc.full_name, specialty: doc.specialty },
      hospital,
      start_time: at(time),
    });

  it('groups by doctor, shows local times and the zone, and asks for the local day', async () => {
    let params;
    server.use(
      http.get(`${API}/appointments`, ({ request }) => {
        params = new URL(request.url).searchParams;
        // Already time-sorted, as the API returns them; Ravi's visit is first of the day.
        return HttpResponse.json(
          onePage([row(1, doctor2, '08:30'), row(2, doctor, '09:00'), row(3, doctor2, '11:30'), row(4, doctor, '14:00')]),
        );
      }),
    );
    renderApp(`/appointments/day?date=${DATE}`);

    const headings = await screen.findAllByRole('heading', { level: 2 });
    expect(headings[0]).toHaveTextContent('Dr. Amara Silva');
    expect(headings[1]).toHaveTextContent('Dr. Ravi Menon');

    const amara = within(headings[0].closest('section'));
    expect(amara.getAllByRole('listitem').map((li) => li.querySelector('time').textContent)).toEqual([
      '09:00',
      '14:00',
    ]);
    expect(screen.getByText(/Times shown in America\/New_York/)).toBeInTheDocument();
    expect(params.get('date_from')).toBe(at('00:00'));
    expect(params.get('date_to')).toBe(localToUtcIso('2099-01-06T00:00'));
  });

  it('shows an empty state and moves a day with the arrows', async () => {
    const user = userEvent.setup();
    renderApp(`/appointments/day?date=${DATE}`);
    expect(await screen.findByText('Nothing booked for this day')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next day' }));
    await waitFor(() => expect(screen.getByLabelText('Date')).toHaveValue('2099-01-06'));
    expect(screen.getByTestId('location').textContent).toBe('/appointments/day?date=2099-01-06');
  });
});
