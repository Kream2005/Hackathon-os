import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import { login as apiLogin } from './api-client'
import Layout from './components/Layout'
import LoginPage from './pages/Login'
import Dashboard from './pages/Dashboard'
import Incidents from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import Alerts from './pages/Alerts'
import OnCall from './pages/OnCall'
import Notifications from './pages/Notifications'
import Metrics from './pages/Metrics'

interface AuthCtx {
  isAuthenticated: boolean
  username: string | null
  logout: () => void
}

export const AuthContext = createContext<AuthCtx>({
  isAuthenticated: false,
  username: null,
  logout: () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export default function App() {
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    setApiKey(localStorage.getItem('api_key'))
    setUsername(localStorage.getItem('username'))
    setChecking(false)
  }, [])

  const handleLogin = useCallback(async (user: string, pass: string) => {
    const resp = await apiLogin(user, pass)
    localStorage.setItem('api_key', resp.api_key)
    localStorage.setItem('username', resp.username)
    setApiKey(resp.api_key)
    setUsername(resp.username)
  }, [])

  const handleLogout = useCallback(() => {
    localStorage.removeItem('api_key')
    localStorage.removeItem('username')
    setApiKey(null)
    setUsername(null)
  }, [])

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
    <AuthContext.Provider value={{ isAuthenticated: true, username, logout: handleLogout }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:id" element={<IncidentDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/oncall" element={<OnCall />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/metrics" element={<Metrics />} />
        </Routes>
      </Layout>
    </AuthContext.Provider>
  )
}
