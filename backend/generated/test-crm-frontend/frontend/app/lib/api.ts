// lib/api.ts
let base = '';
if (typeof window !== 'undefined') {
  // Browser: infer from current path /serve/<id>/
  const m = window.location.pathname.match(/^\/serve\/([^/]+)/);
  base = m ? `/serve/${m[1]}` : '';
} else {
  // Server components (Next): read from .sbhrc.json if present
  try {
    const cfg = require('../.sbhrc.json');
    if (cfg?.build_id) base = `/serve/${cfg.build_id}`;
  } catch {}
}
const API_BASE = `${base}/api`;

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`GET ${path} ${res.status}`);
  return res.json();
}

// Convenience wrappers:
export const getHealth     = () => apiGet<{status:string,service:string}>(`/health`);
export const getAccounts   = () => apiGet<any[]>(`/accounts/`);
export const getContacts   = () => apiGet<any[]>(`/contacts/`);
export const getDeals      = () => apiGet<any[]>(`/deals/`);
export const getPipelines  = () => apiGet<any[]>(`/pipelines/`);
export const getActivities = () => apiGet<any[]>(`/activities/`);
