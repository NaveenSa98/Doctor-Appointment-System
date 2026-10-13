import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import * as authApi from '../api/auth';
import { getToken, setToken, setUnauthorizedHandler } from '../api/client';

const AuthContext = createContext(null);

/** Holds the signed-in user. Sign-in is optional: `user` is null for visitors. */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(getToken()));

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    if (!getToken()) return;
    authApi
      .getMe()
      .then(setUser)
      .catch(() => {
        /* a 401 already cleared the session; other errors leave the visitor anonymous */
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token: token, user: me } = await authApi.login(email, password);
    setToken(token);
    setUser(me);
    return me;
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** @returns {{ user: import('../api/client').User|null, loading: boolean, login: Function, logout: Function }} */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
