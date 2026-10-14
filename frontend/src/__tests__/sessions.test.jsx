import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, hospital } from './mocks/handlers';
import { renderApp } from './test-utils';
import { localToUtcIso } from '../utils/datetime';
import { formatOffset, groupByWeekday } from '../utils/schedule';

const session = (overrides = {}) => ({
  id: 's1',
  hospital,
  weekday: 0,
  start_time: '09:00',
  end_time: '12:00',
  skipped: [],
  ...overrides,
});

const schedule = (sessions) => ({ doctor_id: 'd1', utc_offset_minutes: 330, sessions });

const adminDoctor = {
  id: 'd1',
  full_name: 'Dr. Amara Silva',
  specialty: 'Cardiology',
  is_active: true,
  hospitals: [hospital],
  account: null,
  appointment_count: 0,
};

describe('schedule helpers', () => {
  it('formats the clinic offset', () => {
    expect(formatOffset(0)).toBe('UTC');
    expect(formatOffset(330)).toBe('UTC+05:30');
    expect(formatOffset(-210)).toBe('UTC-03:30');
  });

  it('groups sessions by weekday, Monday first, in time order', () => {
    const groups = groupByWeekday([
      session({ id: 'a', weekday: 2, start_time: '14:00' }),
      session({ id: 'b', weekday: 0 }),
      session({ id: 'c', weekday: 2, start_time: '09:00' }),
    ]);
    expect(groups.map((g) => g.name)).toEqual(['Monday', 'Wednesday']);
    expect(groups[1].sessions.map((s) => s.id)).toEqual(['c', 'a']);
  });
});

describe('admin: weekly sessions', () => {
  beforeEach(() => {
    sessionStorage.setItem('am.token', 'test-token');
    server.use(
      http.get(`${API}/admin/doctors/d1`, () => HttpResponse.json(adminDoctor)),
      http.get(`${API}/doctors/d1/sessions`, () =>
        HttpResponse.json(schedule([session({ skipped: [{ on_date: '2099-01-05', reason: 'Leave' }] })])),
      ),
    );
  });

  it('lists sessions with the clinic clock and skipped dates', async () => {
    renderApp('/admin/doctors/d1');
    const monday = await screen.findByRole('region', { name: 'Monday' });
    expect(monday).toHaveTextContent('09:00–12:00');
    expect(monday).toHaveTextContent('Riverside General');
    expect(monday).toHaveTextContent(/Not running on .*2099.*\(Leave\)/);
    expect(screen.getByText(/Times are clinic time \(UTC\+05:30\)/)).toBeInTheDocument();
  });

  it('explains the default hours while a doctor has no sessions', async () => {
    server.use(http.get(`${API}/doctors/d1/sessions`, () => HttpResponse.json(schedule([]))));
    renderApp('/admin/doctors/d1');
    expect(await screen.findByText(/any time from 09:00 to 16:30/)).toBeInTheDocument();
  });

  it('adds a session', async () => {
    let body;
    server.use(
      http.post(`${API}/admin/doctors/d1/sessions`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(session({ id: 's2', weekday: 2 }), { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await screen.findByRole('region', { name: 'Monday' });

    await user.selectOptions(screen.getByLabelText('Day'), 'Wednesday');
    await user.selectOptions(screen.getByLabelText('From'), '13:00');
    await user.selectOptions(screen.getByLabelText('To'), '17:30');
    await user.click(screen.getByRole('button', { name: 'Add session' }));

    await waitFor(() =>
      expect(body).toEqual({ hospital_id: 'h1', weekday: 2, start_time: '13:00', end_time: '17:30' }),
    );
  });

  it('checks the hours and shows an overlap from the server', async () => {
    server.use(
      http.post(`${API}/admin/doctors/d1/sessions`, () =>
        HttpResponse.json({ error: { code: 'session_overlap', message: 'overlap' } }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await screen.findByRole('region', { name: 'Monday' });

    await user.selectOptions(screen.getByLabelText('To'), '08:00');
    await user.click(screen.getByRole('button', { name: 'Add session' }));
    expect(await screen.findByText('The session must end after it starts.')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('To'), '12:00');
    await user.click(screen.getByRole('button', { name: 'Add session' }));
    expect(await screen.findByText(/already has a session at that time/)).toBeInTheDocument();
  });

  it('skips a date and restores one', async () => {
    let skipBody;
    let restored;
    server.use(
      http.post(`${API}/admin/sessions/s1/skipped-dates`, async ({ request }) => {
        skipBody = await request.json();
        return HttpResponse.json(session(), { status: 201 });
      }),
      http.delete(`${API}/admin/sessions/s1/skipped-dates/2099-01-05`, () => {
        restored = true;
        return HttpResponse.json(session());
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await screen.findByRole('region', { name: 'Monday' });

    await user.click(screen.getByRole('button', { name: 'Skip a date' }));
    fireEvent.change(screen.getByLabelText('Date to skip'), { target: { value: '2099-01-12' } });
    await user.type(screen.getByLabelText('Reason (optional)'), 'Conference');
    await user.click(screen.getByRole('button', { name: 'Skip this date' }));
    await waitFor(() => expect(skipBody).toEqual({ date: '2099-01-12', reason: 'Conference' }));

    await user.click(await screen.findByRole('button', { name: /^Restore/ }));
    await waitFor(() => expect(restored).toBe(true));
  });

  it('asks before removing a session and explains a refusal', async () => {
    let deletes = 0;
    server.use(
      http.delete(`${API}/admin/sessions/s1`, () => {
        deletes += 1;
        return HttpResponse.json({ error: { code: 'session_has_appointments', message: 'x' } }, { status: 409 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/admin/doctors/d1');
    await user.click(await screen.findByRole('button', { name: 'Remove' }));
    const dialog = screen.getByRole('dialog', { name: 'Remove this session?' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(deletes).toBe(0);

    await user.click(screen.getByRole('button', { name: 'Remove' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Remove session' }));
    expect(await screen.findByText(/upcoming appointments in this session/)).toBeInTheDocument();
    expect(deletes).toBe(1);
  });
});

describe('doctor: my schedule', () => {
  beforeEach(() => sessionStorage.setItem('am.token', 'doctor-token'));

  it('shows the sessions read-only', async () => {
    server.use(
      http.get(`${API}/doctors/d1/sessions`, () =>
        HttpResponse.json(schedule([session({ skipped: [{ on_date: '2099-01-05', reason: null }] })])),
      ),
    );
    renderApp('/my-schedule');
    const monday = await screen.findByRole('region', { name: 'Monday' });
    expect(monday).toHaveTextContent('09:00–12:00');
    expect(screen.getByText(/contact an administrator/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Skip a date' })).not.toBeInTheDocument();
  });

  it('says so when no sessions are set, and is only for doctors', async () => {
    const { unmount } = renderApp('/my-schedule');
    expect(await screen.findByText('No sessions set yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'My schedule' })).toBeInTheDocument();
    unmount();

    sessionStorage.setItem('am.token', 'test-token');
    renderApp('/my-schedule');
    expect(await screen.findByRole('heading', { name: 'Appointments' })).toBeInTheDocument();
  });
});

describe('booking uses the doctor’s sessions', () => {
  const DATE = '2099-01-05';
  const at = (time) => localToUtcIso(`${DATE}T${time}`);

  async function choose(user) {
    await user.selectOptions(await screen.findByLabelText('Hospital'), 'h1');
    await user.selectOptions(screen.getByLabelText('Doctor'), 'd1');
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: DATE } });
  }

  it('offers only the session times when the doctor has sessions', async () => {
    server.use(
      http.get(`${API}/doctors/d1/slots`, () =>
        HttpResponse.json({ doctor_id: 'd1', hospital_id: 'h1', restricted: true, slots: [at('10:00'), at('10:30')] }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/book');
    await choose(user);

    expect(await screen.findByRole('button', { name: /^10:00/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /^10:30/ })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /^09:00/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^14:00/ })).not.toBeInTheDocument();
  });

  it('says so when the doctor has no session that day', async () => {
    server.use(
      http.get(`${API}/doctors/d1/slots`, () =>
        HttpResponse.json({ doctor_id: 'd1', hospital_id: 'h1', restricted: true, slots: [] }),
      ),
    );
    const user = userEvent.setup();
    renderApp('/book');
    await choose(user);

    expect(await screen.findByText(/no session on that day/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^09:00/ })).not.toBeInTheDocument();
  });

  it('keeps the default hours for a doctor with no sessions', async () => {
    const user = userEvent.setup();
    renderApp('/book');
    await choose(user);
    expect(await screen.findByRole('button', { name: /^09:00/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /^16:30/ })).toBeEnabled();
  });
});
