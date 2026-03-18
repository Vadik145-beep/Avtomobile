import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  login: (token: string) => void
  logout: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      login: (token) => set({ token }),
      logout: () => set({ token: null }),
      isAuthenticated: () => !!get().token,
    }),
    {
      name: 'avto-lead-auth',
    }
  )
)
