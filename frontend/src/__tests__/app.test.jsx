import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderApp } from './test-utils';

describe('public pages', () => {
  it('renders the home page without a token and with a Sign in link', () => {
    renderApp('/');
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/book your doctor visit/i);
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('does not render a demo banner on the login or booking pages', async () => {
    renderApp('/login');
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
    renderApp('/book');
    expect(await screen.findByRole('heading', { name: 'Book an appointment' })).toBeInTheDocument();
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });
});

describe('ProtectedRoute', () => {
  it('redirects an anonymous visitor from staff pages to /login', async () => {
    renderApp('/appointments');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('lets a signed-in user through and shows the user menu', async () => {
    sessionStorage.setItem('am.token', 'test-token');
    renderApp('/appointments');
    expect(await screen.findByRole('heading', { name: 'Appointments' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument();
  });
});

describe('login', () => {
  it('stores the token and redirects to the staff area on success', async () => {
    const user = userEvent.setup();
    renderApp('/login');
    await user.type(screen.getByLabelText('Email'), 'admin@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('heading', { name: 'Appointments' })).toBeInTheDocument();
    expect(sessionStorage.getItem('am.token')).toBe('test-token');
  });

  it('shows an accessible error on failure and re-enables the form', async () => {
    const user = userEvent.setup();
    renderApp('/login');
    await user.type(screen.getByLabelText('Email'), 'admin@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled());
    expect(sessionStorage.getItem('am.token')).toBeNull();
  });
});
