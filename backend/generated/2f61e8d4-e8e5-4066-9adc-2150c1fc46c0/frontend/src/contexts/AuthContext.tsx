import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../lib/api.ts';

interface User {
  id: number;
  email: string;
  name: string;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  roles: string[];
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [loading, setLoading] = useState(true);

  // Permission mapping for roles
  const rolePermissions: Record<string, string[]> = {
    'Owner': [
      'contacts.read', 'contacts.write', 'contacts.delete',
      'accounts.read', 'accounts.write', 'accounts.delete',
      'deals.read', 'deals.write', 'deals.delete',
      'pipelines.read', 'pipelines.write',
      'activities.read', 'activities.write', 'activities.delete',
      'notes.read', 'notes.write', 'notes.delete',
      'communications.read', 'communications.send',
      'templates.read', 'templates.write', 'templates.delete',
      'automations.read', 'automations.write', 'automations.delete',
      'analytics.read',
      'settings.read', 'settings.write',
      'roles.read', 'roles.write',
      'permissions.read'
    ],
    'Admin': [
      'contacts.read', 'contacts.write', 'contacts.delete',
      'accounts.read', 'accounts.write', 'accounts.delete',
      'deals.read', 'deals.write', 'deals.delete',
      'pipelines.read', 'pipelines.write',
      'activities.read', 'activities.write', 'activities.delete',
      'notes.read', 'notes.write', 'notes.delete',
      'communications.read', 'communications.send',
      'templates.read', 'templates.write', 'templates.delete',
      'automations.read', 'automations.write', 'automations.delete',
      'analytics.read',
      'settings.read', 'settings.write',
      'roles.read', 'roles.write',
      'permissions.read'
    ],
    'Manager': [
      'contacts.read', 'contacts.write',
      'accounts.read', 'accounts.write',
      'deals.read', 'deals.write',
      'pipelines.read', 'pipelines.write',
      'activities.read', 'activities.write',
      'notes.read', 'notes.write',
      'communications.read', 'communications.send',
      'analytics.read'
    ],
    'Sales': [
      'contacts.read', 'contacts.write',
      'accounts.read',
      'deals.read', 'deals.write',
      'pipelines.read',
      'activities.read', 'activities.write',
      'notes.read', 'notes.write',
      'communications.read', 'communications.send',
      'templates.read',
      'analytics.read'
    ],
    'ReadOnly': [
      'contacts.read',
      'accounts.read',
      'deals.read',
      'pipelines.read',
      'activities.read',
      'notes.read',
      'communications.read',
      'templates.read',
      'automations.read',
      'analytics.read'
    ]
  };

  const hasPermission = (permission: string): boolean => {
    if (!user || !user.roles) return false;
    
    for (const role of user.roles) {
      const permissions = rolePermissions[role] || [];
      if (permissions.includes(permission)) {
        return true;
      }
    }
    return false;
  };

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('auth_token', access_token);
      
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
  };

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response);
        } catch (error) {
          console.error('Auth check failed:', error);
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token]);

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    loading,
    hasPermission
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
