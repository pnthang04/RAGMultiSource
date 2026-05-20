"use client";

import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from "react";

import { apiClient, setAuthToken } from "@/lib/api-client";
import type { AuthCredentials, AuthUser } from "@/features/auth/types";

type AuthContextValue = {
  user: AuthUser | null;
  ready: boolean;
  login: (credentials: AuthCredentials) => Promise<void>;
  register: (credentials: AuthCredentials) => Promise<void>;
  logout: () => Promise<void>;
};

const CURRENT_KEY = "rag_chatbot_current_user";

const AuthContext = createContext<AuthContextValue | null>(null);

function readCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CURRENT_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

function persistCurrentUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) {
    window.localStorage.setItem(CURRENT_KEY, JSON.stringify(user));
  } else {
    window.localStorage.removeItem(CURRENT_KEY);
  }
}

function clearAuth() {
  setAuthToken(null);
  persistCurrentUser(null);
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      const cachedUser = readCurrentUser();
      if (cachedUser) {
        setUser(cachedUser);
      }
      try {
        const me = await apiClient.auth.me();
        if (!mounted) return;
        setUser(me);
        persistCurrentUser(me);
      } catch {
        clearAuth();
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setReady(true);
        }
      }
    }

    void bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const login = async ({ email, password }: AuthCredentials) => {
      const response = await apiClient.auth.login({ email, password });
      setAuthToken(response.token);
      setUser(response.user);
      persistCurrentUser(response.user);
    };

    const register = async ({ name, email, password }: AuthCredentials) => {
      const response = await apiClient.auth.register({ name, email, password });
      setAuthToken(response.token);
      setUser(response.user);
      persistCurrentUser(response.user);
    };

    const logout = async () => {
      try {
        await apiClient.auth.logout();
      } finally {
        clearAuth();
        setUser(null);
      }
    };

    return { user, ready, login, register, logout };
  }, [ready, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
