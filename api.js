export class ApiClient {
  constructor(options) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.auth = options.auth || null;
    this.queryParams = options.queryParams || {};
    this.bearerToken = "";
  }

  setBearerToken(token) {
    this.bearerToken = token || "";
  }

  buildHeaders(extra) {
    const headers = { 'Content-Type': 'application/json', ...(extra || {}) };
    if (this.auth && this.auth.type === 'bearer' && this.bearerToken) {
      headers['Authorization'] = `Bearer ${this.bearerToken}`;
    }
    return headers;
  }

  buildUrl(path, query) {
    const url = new URL(this.baseUrl + path);
    const qp = { ...(this.queryParams || {}), ...(query || {}) };
    for (const [k, v] of Object.entries(qp)) {
      if (v === undefined || v === null || v === '') continue;
      url.searchParams.set(k, String(v));
    }
    return url.toString();
  }

  async request(method, path, { query, body } = {}) {
    const res = await fetch(this.buildUrl(path, query), {
      method,
      headers: this.buildHeaders(),
      body: body != null ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${method} ${path} failed: ${res.status} ${res.statusText}${text ? ' - ' + text : ''}`);
    }
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) return res.json();
    return res.text();
  }

  list(resource, { page, limit, sort, order, search, filters } = {}) {
    const query = { page, limit, sort, order, search, ...(filters || {}) };
    return this.request('GET', `/${resource}`, { query });
  }

  get(resource, id) {
    return this.request('GET', `/${resource}/${encodeURIComponent(id)}`);
  }

  create(resource, data) {
    return this.request('POST', `/${resource}`, { body: data });
  }

  update(resource, id, data) {
    return this.request('PUT', `/${resource}/${encodeURIComponent(id)}`, { body: data });
  }

  delete(resource, id) {
    return this.request('DELETE', `/${resource}/${encodeURIComponent(id)}`);
  }
}

