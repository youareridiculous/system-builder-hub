const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function makeRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  // Add auth token if available
  const token = localStorage.getItem('auth_token');
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  async get(endpoint) {
    return makeRequest(endpoint);
  },

  async post(endpoint, body) {
    return makeRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  async put(endpoint, body) {
    return makeRequest(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  async delete(endpoint) {
    return makeRequest(endpoint, {
      method: 'DELETE',
    });
  },

  async patch(endpoint, body) {
    return makeRequest(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },
};
