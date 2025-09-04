// src/lib/api.ts
export const BUILD_ID = (window as any).__SBH_BUILD_ID ?? ""; // optional, injected by SBH UI
const viaServe = !!BUILD_ID;

// Allow direct local dev (vite) and SBH proxy seamlessly:
export const API_BASE = viaServe ? `/serve/${BUILD_ID}/api` : `http://localhost:8000/api`;

// Get auth token from localStorage
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

// Handle 401 responses by redirecting to login
function handleUnauthorized() {
  localStorage.removeItem('auth_token');
  window.location.href = '/login';
}

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { 
    "Content-Type": "application/json", 
    ...(init.headers || {}) 
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers,
    ...init,
  });
  
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error('Unauthorized');
  }
  
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${msg}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: any) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put:  <T>(path: string, body: any) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del:  <T>(path: string) =>
    request<T>(path, { method: "DELETE" }),
};
