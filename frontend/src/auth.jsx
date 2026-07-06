import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem("tj_token");
    if (!token) {
      setReady(true);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
    } catch {
      localStorage.removeItem("tj_token");
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("tj_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const ref = localStorage.getItem("tj_ref") || undefined;
    const { data } = await api.post("/auth/register", { ...payload, ref, origin_url: window.location.origin });
    localStorage.setItem("tj_token", data.token);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem("tj_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
