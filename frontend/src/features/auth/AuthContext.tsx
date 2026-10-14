import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import {
  getAccessToken,
  loadRefreshToken,
  loginRequest,
  meRequest,
  refreshRequest,
  setTokens,
  type UserMe,
} from '@/lib/api'

type AuthContextValue = {
  user: UserMe | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserMe | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const bootstrap = useCallback(async () => {
    try {
      if (!getAccessToken()) {
        const refresh = loadRefreshToken()
        if (!refresh) {
          setIsLoading(false)
          return
        }
        await refreshRequest()
      }
      const me = await meRequest()
      setUser(me)
    } catch {
      setTokens(null)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await loginRequest(email, password)
    setTokens(tokens)
    const me = await meRequest()
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    setTokens(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, isLoading, login, logout }),
    [user, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
