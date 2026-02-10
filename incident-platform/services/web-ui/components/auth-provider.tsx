"use client"

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react"
import { login as apiLogin } from "@/lib/api-client"
import { LoginPage } from "@/components/login-page"

interface AuthContextType {
  isAuthenticated: boolean
  username: string | null
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  username: null,
  logout: () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [checking, setChecking] = useState(true)

  // On mount, check localStorage
  useEffect(() => {
    const stored = localStorage.getItem("api_key")
    const storedUser = localStorage.getItem("username")
    if (stored) {
      setApiKey(stored)
      setUsername(storedUser)
    }
    setChecking(false)
  }, [])

  const handleLogin = useCallback(
    async (user: string, password: string) => {
      const resp = await apiLogin(user, password)
      localStorage.setItem("api_key", resp.api_key)
      localStorage.setItem("username", resp.username)
      setApiKey(resp.api_key)
      setUsername(resp.username)
    },
    [],
  )

  const handleLogout = useCallback(() => {
    localStorage.removeItem("api_key")
    localStorage.removeItem("username")
    setApiKey(null)
    setUsername(null)
  }, [])

  // Don't flash login page while checking localStorage
  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!apiKey) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <AuthContext.Provider
      value={{ isAuthenticated: true, username, logout: handleLogout }}
    >
      {children}
    </AuthContext.Provider>
  )
}
