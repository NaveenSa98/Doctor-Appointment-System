import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { makeAppointment } from './mocks/handlers';
import { renderApp } from './test-utils';
import { downloadReceipt } from '../utils/receiptPdf';

vi.mock('../utils/receiptPdf', () => ({ downloadReceipt: vi.fn() }));

const ID = '3f2a9c1e-7b64-4d0a-9c11-5e8f2a6b7d90';
const appointment = makeAppointment(1, {
  id: ID,
  patient_name: 'Jane Perera',
  appointment_type: 'check_up',
  start_time: '2099-01-05T15:00:00Z',
  created_at: '2098-12-20T08:15:00Z',
});

const open = () => renderApp({ pathname: '/book/confirmed', state: { appointment } });

beforeEach(() => {
  downloadReceipt.mockReset();
  downloadReceipt.mockResolvedValue(undefined);
});

describe('booking confirmation', () => {
  it('shows the reference, the visit details and the guidance text', () => {
    open();
    expect(screen.getByLabelText('Reference number')).toHaveTextContent(ID);
    expect(
      screen.getByText(
        'Keep this reference number. Staff will ask for it when you visit the doctor or need to make any changes.',
      ),
    ).toBeInTheDocument();

    const details = screen.getByRole('article');
    const row = (label) => within(details).getByText(label).closest('div');
    expect(row('Patient')).toHaveTextContent('Jane Perera');
    expect(row('Doctor')).toHaveTextContent('Dr. Amara Silva, Cardiology');
    expect(row('Hospital')).toHaveTextContent('Riverside General');
    expect(row('Visit type')).toHaveTextContent('Check-up');
    expect(row('Status')).toHaveTextContent('Scheduled');
    expect(row('Date and time')).toHaveTextContent(/January 5, 2099/);
    expect(row('Booked on')).toHaveTextContent(/December 20, 2098/);
  });

  it('downloads the PDF for this booking', async () => {
    const user = userEvent.setup();
    open();
    await user.click(screen.getByRole('button', { name: 'Download receipt (PDF)' }));
    expect(downloadReceipt).toHaveBeenCalledWith(appointment);
  });

  it('disables the button while the PDF is being prepared', async () => {
    let finish;
    downloadReceipt.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const user = userEvent.setup();
    open();
    await user.click(screen.getByRole('button', { name: 'Download receipt (PDF)' }));

    const busy = screen.getByRole('button', { name: 'Preparing PDF…' });
    expect(busy).toBeDisabled();
    finish();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Download receipt (PDF)' })).toBeEnabled());
  });

  it('says so when the PDF cannot be created', async () => {
    downloadReceipt.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    open();
    await user.click(screen.getByRole('button', { name: 'Download receipt (PDF)' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not create the PDF');
    expect(screen.getByRole('button', { name: 'Download receipt (PDF)' })).toBeEnabled();
  });

  it('offers My bookings only to a signed-in patient', async () => {
    const { unmount } = open();
    expect(screen.queryByRole('link', { name: 'My bookings' })).not.toBeInTheDocument();
    unmount();

    sessionStorage.setItem('am.token', 'patient-token');
    renderApp({ pathname: '/book/confirmed', state: { appointment } });
    // The header nav has one too, so look inside the receipt.
    const receipt = await screen.findByRole('article');
    expect(await within(receipt).findByRole('link', { name: 'My bookings' })).toHaveAttribute('href', '/my-bookings');
  });
});
