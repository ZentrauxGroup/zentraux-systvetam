/**
 * SYSTVETAM — API Client
 * Zentraux Group LLC
 *
 * Axios instance with JWT injection and 401 auto-logout.
 * Every API call from the dashboard flows through this client.
 *
 * Local dev:  VITE_API_URL unset → baseURL = '/api' → Vite proxy → localhost:8000
 * Production: VITE_API_URL = 'https://dispatch.railway.app' → direct calls
 */

import axios from 'axios';
import { useTowerStore } from '@/store';

// Baked at build time via Railway env var VITE_API_URL
// Falls back to /api for local dev (Vite proxy handles routing)
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}`
  : '/api';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: inject Bearer token
client.interceptors.request.use((config) => {
  const token = useTowerStore.getState().authToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: 401 → clear auth
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      useTowerStore.getState().clearAuth();
    }
    return Promise.reject(error);
  },
);

export { client };
