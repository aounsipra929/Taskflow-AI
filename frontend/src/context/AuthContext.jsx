import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../api/services";
import { tokenStorage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStorage.get()); // restoring session

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  // Restore the session from a stored token.
  useEffect(() => {
    if (!tokenStorage.get()) return;
    authApi
      .me()
      .then((res) => setUser(res.data))
      .catch(() => tokenStorage.clear())
      .finally(() => setLoading(false));
  }, []);

  // The axios interceptor fires this when the token expires.
  useEffect(() => {
    window.addEventListener("auth:logout", logout);
    return () => window.removeEventListener("auth:logout", logout);
  }, [logout]);

  const login = async (email, password) => {
    const { data } = await authApi.login(email, password);
    tokenStorage.set(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const register = (payload) => authApi.register(payload);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, setUser, isAdmin: user?.role === "admin" }),
    [user, loading, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
