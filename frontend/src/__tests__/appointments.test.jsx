import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { API, emptyPage, makeAppointment } from './mocks/handlers';
import { renderApp } from './test-utils';

/** Serve a 3-page result set and record every request URL. */
function servePages(requests) {
  server.use(
    http.get(`${API}/appointments`, ({ request }) => {
      const url = new URL(request.url);
      requests.push(url);
      const page = Number(url.searchParams.get('page') ?? 1);
      return HttpResponse.json({
        items: [makeAppointment(page, { patient_name: `Jane Page${page}` })],
        total: 41,
        page,
        page_size: 20,
        pages: 3,
      });
    }),
  );
}

const location = () => screen.getByTestId('location').textContent;

beforeEach(() => sessionStorage.setItem('am.token', 'test-token'));

describe('appointments list', () => {
  it('debounces search: one request for a burst of typing', async () => {
    const requests = [];
    servePages(requests);
    const user = userEvent.setup();
    renderApp('/appointments');
    await screen.findByText('Jane Page1');

    await user.type(screen.getByRole('searchbox', { name: 'Search patient name' }), 'jane');
    await waitFor(() => expect(location()).toBe('/appointments?q=jane'));

    expect(requests.filter((u) => u.searchParams.has('q'))).toHaveLength(1);
    expect(requests.at(-1).searchParams.get('q')).toBe('jane');
  });

  it('restores filters from the URL (so they survive a reload) and sends them to the API', async () => {
    const requests = [];
    servePages(requests);
    renderApp('/appointments?q=jane&status=confirmed&status=scheduled&sort=-patient_name&page=2');
    await screen.findByText('Jane Page2');

    expect(screen.getByRole('searchbox')).toHaveValue('jane');
    expect(screen.getByRole('checkbox', { name: 'Confirmed' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Completed' })).not.toBeChecked();

    const params = requests.at(-1).searchParams;
    expect(params.get('q')).toBe('jane');
    expect(params.getAll('status')).toEqual(['confirmed', 'scheduled']);
    expect(params.get('sort')).toBe('-patient_name');
    expect(params.get('page')).toBe('2');
  });

  it('resets to page 1 when a filter changes', async () => {
    servePages([]);
    const user = userEvent.setup();
    renderApp('/appointments?page=2');
    await screen.findByText('Jane Page2');

    await user.click(screen.getByRole('checkbox', { name: 'Confirmed' }));
    await waitFor(() => expect(location()).toBe('/appointments?status=confirmed'));
  });

  it('disables Previous on the first page and Next on the last', async () => {
    servePages([]);
    const { unmount } = renderApp('/appointments');
    await screen.findByText('Jane Page1');
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
    expect(screen.getByRole('status')).toHaveTextContent('Showing 1 to 20 of 41');
    unmount();

    renderApp('/appointments?page=3');
    await screen.findByText('Jane Page3');
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled();
  });

  it('sorts by clicking a column header', async () => {
    servePages([]);
    const user = userEvent.setup();
    renderApp('/appointments');
    await screen.findByText('Jane Page1');
    await user.click(screen.getByRole('button', { name: /^Patient/ }));
    await waitFor(() => expect(location()).toBe('/appointments?sort=patient_name'));
  });

  it('shows the empty state with a working Clear filters button', async () => {
    const user = userEvent.setup();
    renderApp('/appointments?status=cancelled');
    expect(await screen.findByText('No appointments match your filters')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(await screen.findByText('No appointments yet')).toBeInTheDocument();
    expect(location()).toBe('/appointments');
  });

  it('shows an error state with a retry button', async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/appointments`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ error: { code: 'server_error', message: 'boom' } }, { status: 500 })
          : HttpResponse.json({ ...emptyPage(), items: [makeAppointment(1)], total: 1, pages: 1 });
      }),
    );
    const user = userEvent.setup();
    renderApp('/appointments');
    const alert = await screen.findByRole('alert');
    await user.click(within(alert).getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Patient 1')).toBeInTheDocument();
  });
});
