// src/lib/api.ts
export const BUILD_ID = (window as any).__SBH_BUILD_ID ?? ""; // optional, injected by SBH UI
const viaServe = !!BUILD_ID;

// Allow direct local dev (vite) and SBH proxy seamlessly:
export const API_BASE = viaServe ? `/serve/${BUILD_ID}/api` : `http://localhost:8000/api`;

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    ...init,
  });
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
