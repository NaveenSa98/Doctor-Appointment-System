import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { doctor, doctor2, hospital, hospital2 } from './mocks/handlers';
import { renderApp } from './test-utils';
import { filterDoctors, specialtiesOf } from '../utils/doctorSearch';

const doctors = [
  doctor, // Dr. Amara Silva, Cardiology, visits both hospitals
  doctor2, // Dr. Ravi Menon, Dermatology, visits St. Mary's only
  { id: 'd3', full_name: 'Dr. José Fernández', specialty: 'Cardiology', hospitals: [hospital] },
];

describe('filterDoctors', () => {
  it('matches every typed word in any order, ignoring case, accents and "Dr."', () => {
    expect(filterDoctors(doctors, { name: 'AMARA' }).map((d) => d.id)).toEqual(['d1']);
    expect(filterDoctors(doctors, { name: 'silva amara' }).map((d) => d.id)).toEqual(['d1']);
    expect(filterDoctors(doctors, { name: 'dr. ravi' }).map((d) => d.id)).toEqual(['d2']);
    expect(filterDoctors(doctors, { name: 'jose fernandez' }).map((d) => d.id)).toEqual(['d3']);
    expect(filterDoctors(doctors, { name: 'zzz' })).toEqual([]);
  });

  it('narrows by specialty and hospital, and an empty search matches everyone', () => {
    expect(filterDoctors(doctors, { specialty: 'Cardiology' }).map((d) => d.id)).toEqual(['d1', 'd3']);
    expect(filterDoctors(doctors, { hospitalId: 'h2' }).map((d) => d.id)).toEqual(['d1', 'd2']);
    expect(filterDoctors(doctors, { specialty: 'Cardiology', hospitalId: 'h2' }).map((d) => d.id)).toEqual(['d1']);
    expect(filterDoctors(doctors)).toHaveLength(3);
  });

  it('lists each specialty once, A to Z', () => {
    expect(specialtiesOf(doctors)).toEqual(['Cardiology', 'Dermatology']);
  });
});

describe('doctor search on the booking page', () => {
  const search = () => screen.getByRole('button', { name: 'Search' });
  const panel = () => screen.getByRole('region', { name: 'Find a doctor' });

  async function openBooking() {
    const view = renderApp('/book');
    await screen.findByLabelText('Hospital'); // the booking form below has loaded
    return view;
  }

  it('shows the search bar with the four fields and lists nobody until you search', async () => {
    await openBooking();
    const bar = within(panel());
    expect(bar.getByLabelText('Doctor name')).toBeInTheDocument();
    expect(bar.getByLabelText('Specialization')).toBeInTheDocument();
    expect(bar.getByLabelText('Filter by hospital')).toBeInTheDocument();
    expect(bar.getByLabelText('Preferred date')).toBeInTheDocument();
    expect(bar.queryByRole('status')).not.toBeInTheDocument();
  });

  it('offers the specialties and hospitals from the doctors list', async () => {
    await openBooking();
    const options = (label) =>
      within(within(panel()).getByLabelText(label)).getAllByRole('option').map((o) => o.textContent);
    expect(options('Specialization')).toEqual(['Select specialization', 'Cardiology', 'Dermatology']);
    expect(options('Filter by hospital')).toEqual(['Select hospital', hospital.name, hospital2.name]);
  });

  it('finds a doctor by name and fills the booking form when you choose them', async () => {
    const user = userEvent.setup();
    await openBooking();
    await user.type(within(panel()).getByLabelText('Doctor name'), 'ravi');
    await user.click(search());

    expect(await within(panel()).findByRole('status')).toHaveTextContent('1 doctor found');
    expect(within(panel()).getByText('Dr. Ravi Menon')).toBeInTheDocument();
    expect(within(panel()).queryByText('Dr. Amara Silva')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Book with Dr. Ravi Menon' }));
    await waitFor(() => expect(screen.getByLabelText('Doctor')).toHaveValue('d2'));
    // Dr. Menon visits one hospital, so it is chosen for you.
    await waitFor(() => expect(screen.getByLabelText('Hospital')).toHaveValue('h2'));
  });

  it('carries the hospital and date from the search into the form', async () => {
    const user = userEvent.setup();
    await openBooking();
    await user.selectOptions(within(panel()).getByLabelText('Filter by hospital'), 'h1');
    fireEvent.change(within(panel()).getByLabelText('Preferred date'), { target: { value: '2099-01-05' } });
    await user.click(search());

    expect(await within(panel()).findByRole('status')).toHaveTextContent('1 doctor found'); // only d1 visits h1
    await user.click(screen.getByRole('button', { name: 'Book with Dr. Amara Silva' }));

    await waitFor(() => expect(screen.getByLabelText('Doctor')).toHaveValue('d1'));
    await waitFor(() => expect(screen.getByLabelText('Hospital')).toHaveValue('h1'));
    expect(screen.getByLabelText('Date')).toHaveValue('2099-01-05');
  });

  it('filters by specialization', async () => {
    const user = userEvent.setup();
    await openBooking();
    await user.selectOptions(within(panel()).getByLabelText('Specialization'), 'Dermatology');
    await user.click(search());
    expect(await within(panel()).findByText('Dr. Ravi Menon')).toBeInTheDocument();
    expect(within(panel()).queryByText('Dr. Amara Silva')).not.toBeInTheDocument();
  });

  it('lists everyone when you search with nothing filled in', async () => {
    const user = userEvent.setup();
    await openBooking();
    await user.click(search());
    expect(await within(panel()).findByRole('status')).toHaveTextContent('2 doctors found');
  });

  it('says so when nobody matches, and Clear resets the bar', async () => {
    const user = userEvent.setup();
    await openBooking();
    const name = within(panel()).getByLabelText('Doctor name');
    await user.type(name, 'nobody');
    await user.click(search());
    expect(await within(panel()).findByRole('status')).toHaveTextContent('No doctors match your search');

    await user.click(within(panel()).getByRole('button', { name: 'Clear' }));
    expect(within(panel()).queryByRole('status')).not.toBeInTheDocument();
    expect(name).toHaveValue('');
  });

  it('is not shown to a signed-in doctor, who books for themself', async () => {
    sessionStorage.setItem('am.token', 'doctor-token');
    renderApp('/book');
    await screen.findByLabelText('Hospital');
    expect(screen.queryByRole('region', { name: 'Find a doctor' })).not.toBeInTheDocument();
  });
});
