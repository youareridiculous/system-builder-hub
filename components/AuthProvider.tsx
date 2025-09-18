'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { CognitoUser, AuthenticationDetails, CognitoUserPool } from 'amazon-cognito-identity-js'

interface AuthContextType {
  user: CognitoUser | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CognitoUser | null>(null)
  const [loading, setLoading] = useState(true)

  // Get environment variables with fallbacks
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || 'us-west-2_1kCtllr1G'
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '1c44jrscj09u4358t4f4qktn31'

  const userPool = new CognitoUserPool({
    UserPoolId: userPoolId,
    ClientId: clientId
  })

  useEffect(() => {
    // Check for existing session
    const currentUser = userPool.getCurrentUser()
    if (currentUser) {
      currentUser.getSession((err: any, session: any) => {
        if (err) {
          setUser(null)
        } else {
          setUser(currentUser)
        }
        setLoading(false)
      })
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    return new Promise<void>((resolve, reject) => {
      const authenticationDetails = new AuthenticationDetails({
        Username: email,
        Password: password
      })

      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool
      })

      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (result) => {
          setUser(cognitoUser)
          resolve()
        },
        onFailure: (err) => {
          reject(err)
        }
      })
    })
  }

  const logout = () => {
    if (user) {
      user.signOut()
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      isAuthenticated: !!user,
      loading
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
