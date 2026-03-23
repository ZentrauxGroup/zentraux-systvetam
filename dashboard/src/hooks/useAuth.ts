/**
 * SYSTVETAM — Auth Hook
 * Zentraux Group LLC
 *
 * POST /api/auth/token on login.
 * GET /api/auth/me on mount to restore session from localStorage.
 * Expose: login(), logout(), currentUser, isAuthenticated.
 */

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { useTowerStore } from '@/store';
import type { AuthUser, TokenResponse } from '@/types';

// Same env-aware base as api/client.ts
// Dev: VITE_API_URL unset → '/api' → Vite proxy → localhost:8000
// Prod: VITE_API_URL = 'https://dispatch.railway.app' → direct calls
const AUTH_BASE = import.meta.env.VITE_API_URL ?? '/api';
const api = axios.create({ baseURL: AUTH_BASE });

interface UseAuthReturn {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  currentUser: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useAuth(): UseAuthReturn {
  const { authToken, currentUser, setAuth, clearAuth } = useTowerStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore session on mount
  useEffect(() => {
    if (authToken && !currentUser) {
      restoreSession();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const restoreSession = async () => {
    if (!authToken) return;
    setIsLoading(true);
    try {
      const { data } = await api.get<{ agent_id: string; role: string; display_name: string }>(
        '/auth/me',
        { headers: { Authorization: `Bearer ${authToken}` } },
      );
      const user: AuthUser = {
        agent_id: data.agent_id,
        role: data.role as AuthUser['role'],
        display_name: data.display_name,
      };
      setAuth(authToken, user);
    } catch {
      // Token expired or invalid — clear
      clearAuth();
    } finally {
      setIsLoading(false);
    }
  };

  const login = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const { data } = await api.post<TokenResponse>('/auth/token', {
          username,
          password,
        });
        const user: AuthUser = {
          agent_id: data.agent_id,
          role: data.role as AuthUser['role'],
          display_name: data.display_name,
        };
        setAuth(data.access_token, user);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          setError('Invalid credentials.');
        } else {
          setError('Connection failed. Is Dispatch running?');
        }
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [setAuth],
  );

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  return {
    login,
    logout,
    currentUser,
    isAuthenticated: !!authToken && !!currentUser,
    isLoading,
    error,
  };
}
