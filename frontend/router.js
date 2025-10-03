export class Router {
  constructor() {
    this.routes = [];
    window.addEventListener('popstate', () => this._handle());
    document.addEventListener('click', (e) => {
      const a = e.target.closest('a');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('#')) return;
      e.preventDefault();
      this.push(href);
    });
  }

  addRoute(pattern, handler) {
    const keys = [];
    const regex = this._compile(pattern, keys);
    this.routes.push({ pattern, regex, keys, handler });
  }

  start() {
    this._handle();
  }

  push(path) {
    history.pushState({}, '', path);
    this._handle();
  }

  replace(path) {
    history.replaceState({}, '', path);
    this._handle();
  }

  _compile(pattern, keys) {
    const parts = pattern.split('/').filter(Boolean);
    const regexParts = parts.map((p) => {
      if (p.startsWith(':')) { keys.push(p.slice(1)); return '([^/]+)'; }
      return p.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    });
    const regex = new RegExp('^/' + regexParts.join('/') + '/?$');
    return regex;
  }

  _handle() {
    const url = new URL(location.href);
    const path = url.pathname;
    for (const r of this.routes) {
      const m = path.match(r.regex);
      if (m) {
        const params = {};
        r.keys.forEach((k, i) => params[k] = decodeURIComponent(m[i + 1] || ''));
        const query = Object.fromEntries(url.searchParams.entries());
        r.handler({ params, query });
        return true;
      }
    }
    return false;
  }
}

