'use client'

import { createContext, useContext, useState, useEffect } from 'react'

interface AuthContextType {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function SimpleAuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is already logged in (from localStorage)
    const savedAuth = localStorage.getItem('sbh-auth')
    if (savedAuth === 'true') {
      setIsAuthenticated(true)
    }
    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    // Simple authentication check
    if (email === 'admin@sbh.com' && password === 'TempPass123!@#') {
      setIsAuthenticated(true)
      localStorage.setItem('sbh-auth', 'true')
    } else {
      throw new Error('Invalid credentials')
    }
  }

  const logout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem('sbh-auth')
  }

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      login,
      logout,
      loading
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within SimpleAuthProvider')
  }
  return context
}
