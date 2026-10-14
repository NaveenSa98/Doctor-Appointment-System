import { screen, within } from '@testing-library/react';
import { renderApp } from './test-utils';

describe('home page', () => {
  it('explains how booking works in four steps', () => {
    renderApp('/');
    const section = screen.getByRole('region', { name: 'How it works' });
    const steps = within(section).getAllByRole('listitem');

    expect(steps).toHaveLength(4);
    expect(steps.map((s) => within(s).getByRole('heading', { level: 3 }).textContent)).toEqual([
      'Find your doctor',
      'Choose a time',
      'Confirm in one step',
      'Keep your reference',
    ]);
    expect(within(section).getByRole('link', { name: 'Start booking' })).toHaveAttribute('href', '/book');
  });

  it('offers booking and sign-up from the first screen', () => {
    renderApp('/');
    expect(screen.getByRole('link', { name: 'Book an appointment' })).toHaveAttribute('href', '/book');
    expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/signup');
    expect(screen.getByRole('region', { name: 'Why DocEase' })).toHaveTextContent('No double bookings');
  });

  it('shows the footer on every page, including that the data is synthetic', () => {
    renderApp('/login');
    const footer = screen.getByRole('contentinfo');
    expect(within(footer).getByRole('link', { name: 'Find a doctor' })).toHaveAttribute('href', '/book');
    expect(footer).toHaveTextContent(/synthetic/i);
  });
});

describe('booking form', () => {
  it('is split into numbered steps', async () => {
    renderApp('/book');
    expect(await screen.findByRole('heading', { name: /Choose your doctor and date/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Pick a time/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Patient details/ })).toBeInTheDocument();
  });
});
