import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  // Restore the session from a stored token on first load.
  useEffect(() => {
    if (!getToken()) return;
    api
      .get("/auth/me")
      .then((d) => setUser(d.user))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  // Any 401 from the API (expired token) logs the user out everywhere.
  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener("campusfix:unauthorized", onUnauthorized);
    return () => window.removeEventListener("campusfix:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (email, password) => {
    const d = await api.post("/auth/login", { email, password });
    setToken(d.token);
    setUser(d.user);
    return d.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
