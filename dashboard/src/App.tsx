/**
 * SYSTVETAM — App Root
 * Zentraux Group LLC
 *
 * Auth guard → TowerLayout (which owns floor rendering).
 * React Query provider for API data.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TowerLayout } from '@/components/layout/TowerLayout';
import { useAuth } from '@/hooks/useAuth';
import { LoginScreen } from '@/floors/LoginScreen';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 2,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}

function AppInner() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-obsidian flex items-center justify-center">
        <span className="text-sm font-mono text-gold animate-pulse tracking-[0.3em]">
          SYSTVETAM
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return <TowerLayout />;
}
