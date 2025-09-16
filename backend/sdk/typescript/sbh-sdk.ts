/**
 * SBH SDK for TypeScript (React/Next.js)
 * Provides auth helpers, RBAC hooks, API client, and event tracking.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Types
export interface SBHUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tenantId: string;
  permissions: string[];
}

export interface SBHContext {
  user: SBHUser | null;
  tenantId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface SBHConfig {
  apiUrl: string;
  authToken?: string;
}

export interface SBHApiResponse<T = any> {
  data: T;
  meta?: any;
  errors?: any[];
}

// API Client
export class SBHApiClient {
  private client: AxiosInstance;
  private config: SBHConfig;

  constructor(config: SBHConfig) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.apiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (config.authToken) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${config.authToken}`;
    }

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          console.error('Authentication failed');
        } else if (error.response?.status === 403) {
          console.error('Access denied');
        }
        throw error;
      }
    );
  }

  async get<T>(endpoint: string, params?: any): Promise<SBHApiResponse<T>> {
    const response: AxiosResponse<SBHApiResponse<T>> = await this.client.get(endpoint, { params });
    return response.data;
  }

  async post<T>(endpoint: string, data?: any): Promise<SBHApiResponse<T>> {
    const response: AxiosResponse<SBHApiResponse<T>> = await this.client.post(endpoint, data);
    return response.data;
  }

  async put<T>(endpoint: string, data?: any): Promise<SBHApiResponse<T>> {
    const response: AxiosResponse<SBHApiResponse<T>> = await this.client.put(endpoint, data);
    return response.data;
  }

  async delete<T>(endpoint: string): Promise<SBHApiResponse<T>> {
    const response: AxiosResponse<SBHApiResponse<T>> = await this.client.delete(endpoint);
    return response.data;
  }

  // Auth methods
  async login(credentials: { email: string; password: string }): Promise<{ token: string; user: SBHUser }> {
    const response = await this.post('/api/auth/login', credentials);
    return response.data;
  }

  async getProfile(): Promise<SBHUser> {
    const response = await this.get('/api/auth/profile');
    return response.data;
  }

  async logout(): Promise<void> {
    await this.post('/api/auth/logout');
  }

  // Analytics methods
  async track(event: string, properties?: any, userId?: string): Promise<void> {
    await this.post('/api/analytics/track', {
      event,
      properties: properties || {},
      userId,
      timestamp: new Date().toISOString(),
    });
  }

  async identify(userId: string, traits?: any): Promise<void> {
    await this.post('/api/analytics/identify', {
      userId,
      traits: traits || {},
      timestamp: new Date().toISOString(),
    });
  }
}

// React Context
const SBHContext = createContext<{
  api: SBHApiClient;
  context: SBHContext;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  track: (event: string, properties?: any) => Promise<void>;
} | null>(null);

// Provider Component
interface SBHProviderProps {
  children: ReactNode;
  config: SBHConfig;
}

export function SBHProvider({ children, config }: SBHProviderProps) {
  const [api] = useState(() => new SBHApiClient(config));
  const [context, setContext] = useState<SBHContext>({
    user: null,
    tenantId: null,
    isAuthenticated: false,
    isLoading: true,
  });

  useEffect(() => {
    // Check for existing auth token
    const token = localStorage.getItem('sbh_auth_token');
    if (token) {
      api.config.authToken = token;
      loadProfile();
    } else {
      setContext(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const loadProfile = async () => {
    try {
      const user = await api.getProfile();
      setContext({
        user,
        tenantId: user.tenantId,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      localStorage.removeItem('sbh_auth_token');
      setContext({
        user: null,
        tenantId: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  };

  const login = async (credentials: { email: string; password: string }) => {
    try {
      const { token, user } = await api.login(credentials);
      localStorage.setItem('sbh_auth_token', token);
      api.config.authToken = token;
      
      setContext({
        user,
        tenantId: user.tenantId,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('sbh_auth_token');
      api.config.authToken = undefined;
      setContext({
        user: null,
        tenantId: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  };

  const track = async (event: string, properties?: any) => {
    try {
      await api.track(event, properties, context.user?.id);
    } catch (error) {
      console.error('Analytics error:', error);
    }
  };

  return (
    <SBHContext.Provider value={{ api, context, login, logout, track }}>
      {children}
    </SBHContext.Provider>
  );
}

// Hook
export function useSBH() {
  const context = useContext(SBHContext);
  if (!context) {
    throw new Error('useSBH must be used within an SBHProvider');
  }
  return context;
}

// API Hook
export function useSBHApi() {
  const { api } = useSBH();
  return api;
}

// Auth Hook
export function useSBHAuth() {
  const { context, login, logout } = useSBH();
  return {
    user: context.user,
    isAuthenticated: context.isAuthenticated,
    isLoading: context.isLoading,
    login,
    logout,
  };
}

// Analytics Hook
export function useSBHAnalytics() {
  const { track } = useSBH();
  return { track };
}

// RBAC Hooks
export function useRequireAuth() {
  const { context } = useSBH();
  
  if (context.isLoading) {
    return { loading: true };
  }
  
  if (!context.isAuthenticated) {
    throw new Error('Authentication required');
  }
  
  return { loading: false };
}

export function useRequireRole(roles: string[]) {
  const { context } = useSBH();
  
  if (context.isLoading) {
    return { loading: true };
  }
  
  if (!context.isAuthenticated) {
    throw new Error('Authentication required');
  }
  
  if (!context.user || !roles.includes(context.user.role)) {
    throw new Error(`Role required: ${roles.join(', ')}`);
  }
  
  return { loading: false };
}

export function useRequirePermission(permission: string) {
  const { context } = useSBH();
  
  if (context.isLoading) {
    return { loading: true };
  }
  
  if (!context.isAuthenticated) {
    throw new Error('Authentication required');
  }
  
  if (!context.user || !context.user.permissions.includes(permission)) {
    throw new Error(`Permission required: ${permission}`);
  }
  
  return { loading: false };
}

// API Hooks
export function useApi<T = any>(endpoint: string, params?: any) {
  const { api } = useSBH();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.get<T>(endpoint, params);
        setData(response.data);
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [endpoint, JSON.stringify(params)]);

  return { data, loading, error };
}

export function useApiMutation<T = any>(endpoint: string) {
  const { api } = useSBH();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = async (data?: any): Promise<T | null> => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post<T>(endpoint, data);
      return response.data;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { mutate, loading, error };
}

// Example Components
export function ContactsList() {
  const { data, loading, error } = useApi<any[]>('/api/contacts');
  const { track } = useSBHAnalytics();

  useEffect(() => {
    track('contacts.list.viewed');
  }, []);

  if (loading) return <div>Loading contacts...</div>;
  if (error) return <div>Error loading contacts: {error.message}</div>;

  return (
    <ul>
      {data?.map(contact => (
        <li key={contact.id}>{contact.first_name} {contact.last_name}</li>
      ))}
    </ul>
  );
}

export function CreateContactForm() {
  const { mutate, loading } = useApiMutation('/api/contacts');
  const { track } = useSBHAnalytics();

  const handleSubmit = async (formData: any) => {
    const result = await mutate(formData);
    if (result) {
      track('contact.created', { contactId: result.id });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Contact'}
      </button>
    </form>
  );
}

// Protected Component Example
export function ProtectedContactsList() {
  useRequirePermission('contacts.read');

  return <ContactsList />;
}

export function AdminOnlyComponent() {
  useRequireRole(['admin', 'owner']);

  return <div>Admin only content</div>;
}
