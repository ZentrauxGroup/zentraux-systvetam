/**
 * SYSTVETAM — Login Screen
 * Zentraux Group LLC
 *
 * Minimal auth gate. Dark glass aesthetic.
 * Posts to /api/auth/token via useAuth hook.
 */

import { useState, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { Hexagon, LogIn, AlertCircle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export function LoginScreen() {
  const { login, isLoading, error } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await login(username, password);
    } catch {
      // Error state handled by useAuth
    }
  };

  return (
    <div className="h-screen w-screen bg-obsidian flex items-center justify-center font-body">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-xs px-6"
      >
        {/* Wordmark */}
        <div className="flex flex-col items-center gap-3 mb-10">
          <Hexagon className="w-8 h-8 text-gold" strokeWidth={1.2} />
          <h1 className="text-xl font-mono font-bold tracking-[0.3em] text-gold">
            SYSTVETAM
          </h1>
          <p className="text-xxs font-mono text-glass-muted tracking-widest">
            TOWER DASHBOARD
          </p>
        </div>

        {/* Login Form */}
        <div className="space-y-4" role="form">
          <div>
            <label className="block text-xxs font-mono text-glass-muted mb-1.5 tracking-wider">
              OPERATOR
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="callsign"
              autoComplete="username"
              className="
                w-full px-3 py-2.5 rounded-circuit
                bg-glass border border-glass-border
                text-sm font-mono text-glass-text placeholder:text-glass-muted/50
                focus:outline-none focus:border-gold/40
                transition-colors
              "
            />
          </div>

          <div>
            <label className="block text-xxs font-mono text-glass-muted mb-1.5 tracking-wider">
              CREDENTIAL
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="
                w-full px-3 py-2.5 rounded-circuit
                bg-glass border border-glass-border
                text-sm font-mono text-glass-text placeholder:text-glass-muted/50
                focus:outline-none focus:border-gold/40
                transition-colors
              "
            />
          </div>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 text-status-error text-xs font-mono"
            >
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              {error}
            </motion.div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={isLoading || !username || !password}
            className="
              w-full flex items-center justify-center gap-2
              px-4 py-2.5 rounded-circuit
              bg-gold/10 border border-gold/30 text-gold
              hover:bg-gold/20 hover:border-gold/50
              disabled:opacity-30 disabled:cursor-not-allowed
              transition-all duration-200
              font-mono text-sm tracking-wider
            "
          >
            <LogIn className="w-4 h-4" />
            {isLoading ? 'AUTHENTICATING...' : 'ENTER'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
