/**
 * Global state store — Zustand
 *
 * Manages player preferences, auth session, and notification queue.
 * State is persisted to localStorage via the persist middleware.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ─── Player Store ─────────────────────────────────────────────────────────────
export const usePlayerStore = create(
  persist(
    (set) => ({
      volume: 1.0,
      isMuted: false,
      autoplay: true,
      preferredQuality: -1, // -1 = Auto
      setVolume: (v) => set({ volume: v }),
      setMuted: (m) => set({ isMuted: m }),
      setAutoplay: (a) => set({ autoplay: a }),
      setPreferredQuality: (q) => set({ preferredQuality: q }),
    }),
    { name: 'bf-player' }
  )
);

// ─── Auth Store ───────────────────────────────────────────────────────────────
export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => set({ user, token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
      updateUser: (patch) => set((s) => ({ user: { ...s.user, ...patch } })),
    }),
    { name: 'bf-auth' }
  )
);

// ─── Notification Store ───────────────────────────────────────────────────────
export const useNotificationStore = create((set, get) => ({
  queue: [],
  push: (msg, type = 'info') =>
    set((s) => ({
      queue: [...s.queue, { id: Date.now(), msg, type }],
    })),
  dismiss: (id) =>
    set((s) => ({ queue: s.queue.filter((n) => n.id !== id) })),
  clear: () => set({ queue: [] }),
}));
