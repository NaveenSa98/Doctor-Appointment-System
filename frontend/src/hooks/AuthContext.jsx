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

  const startSession = useCallback(({ access_token: token, user: me }) => {
    setToken(token);
    setUser(me);
    return me;
  }, []);

  const login = useCallback(
    async (email, password) => startSession(await authApi.login(email, password)),
    [startSession],
  );

  /** Create a patient account and sign it in. */
  const register = useCallback(
    async (fullName, email, password) =>
      startSession(await authApi.register(fullName, email, password)),
    [startSession],
  );

  const value = useMemo(
    () => ({ user, loading, login, register, logout, setUser }),
    [user, loading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** @returns {{ user: import('../api/client').User|null, loading: boolean, login: Function, register: Function, logout: Function, setUser: Function }} */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
