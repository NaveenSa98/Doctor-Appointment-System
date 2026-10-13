import { render } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../hooks/AuthContext';
import AppRoutes from '../routes';

function LocationProbe() {
  const { pathname, search } = useLocation();
  // A <div>, not <output>: <output> has the ARIA role "status", which collides with real status text.
  return <div data-testid="location">{`${pathname}${search}`}</div>;
}

/** Render the real route tree at `path` with fresh providers. */
export function renderApp(path = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
          <LocationProbe />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}
