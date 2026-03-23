import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      /* ================================================================
         ZEN-CIRCUIT — Design Token System
         Zentraux Group LLC
         Dark glass aesthetic. Gold accents. Operator-grade clarity.
         ================================================================ */

      colors: {
        gold: {
          DEFAULT: '#C9A84C',
          light: '#E8C97A',
          dark: '#8C6D2F',
          muted: 'rgba(201, 168, 76, 0.15)',
          pulse: 'rgba(201, 168, 76, 0.4)',
        },
        obsidian: {
          DEFAULT: '#0A0A0F',
          surface: '#12121A',
          panel: '#1A1A26',
          elevated: '#22222E',
        },
        glass: {
          DEFAULT: 'rgba(255, 255, 255, 0.04)',
          border: 'rgba(255, 255, 255, 0.08)',
          hover: 'rgba(255, 255, 255, 0.06)',
          text: 'rgba(248, 248, 240, 0.85)',
          muted: 'rgba(248, 248, 240, 0.45)',
        },
        status: {
          active: '#00FF88',
          idle: '#4A9EFF',
          executing: '#C9A84C',
          error: '#FF4444',
          offline: '#444455',
          gate: '#E8A030',
        },
      },

      fontFamily: {
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },

      fontSize: {
        'xxs': ['0.625rem', { lineHeight: '0.875rem' }],
      },

      backdropBlur: {
        xs: '2px',
      },

      borderRadius: {
        'circuit': '6px',
      },

      boxShadow: {
        'glass': '0 0 0 1px rgba(255, 255, 255, 0.06), 0 4px 24px rgba(0, 0, 0, 0.4)',
        'glass-hover': '0 0 0 1px rgba(201, 168, 76, 0.2), 0 8px 32px rgba(0, 0, 0, 0.5)',
        'gold-glow': '0 0 20px rgba(201, 168, 76, 0.3)',
        'gate-ring': '0 0 0 2px rgba(232, 160, 48, 0.6)',
      },

      animation: {
        'pulse-gold': 'pulse-gold 1.5s ease-in-out infinite',
        'pulse-red': 'pulse-red 0.8s ease-in-out infinite',
        'gate-ring': 'gate-ring 2.0s ease-in-out infinite',
        'fade-in': 'fade-in 0.4s ease-out forwards',
        'slide-up': 'slide-up 0.5s ease-out forwards',
        'floor-enter': 'floor-enter 0.3s ease-out forwards',
        'roster-stagger': 'fade-in 0.3s ease-out forwards',
        'shimmer': 'shimmer 2s ease-in-out infinite',
      },

      keyframes: {
        'pulse-gold': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(201, 168, 76, 0)' },
          '50%': { boxShadow: '0 0 0 6px rgba(201, 168, 76, 0.3)' },
        },
        'pulse-red': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(255, 68, 68, 0)' },
          '50%': { boxShadow: '0 0 0 6px rgba(255, 68, 68, 0.4)' },
        },
        'gate-ring': {
          '0%, 100%': { borderColor: 'rgba(232, 160, 48, 1)', opacity: '1' },
          '50%': { borderColor: 'rgba(201, 168, 76, 1)', opacity: '0.6' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'floor-enter': {
          from: { opacity: '0', transform: 'translateX(20px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'shimmer': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
