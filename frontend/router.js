export class Router {
  constructor(options = {}) {
    this.routes = [];
    this.basePath = (options.basePath || '').replace(/\/$/, '');
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
    history.pushState({}, '', this.to(path));
    this._handle();
  }

  replace(path) {
    history.replaceState({}, '', this.to(path));
    this._handle();
  }

  to(path) {
    if (!path.startsWith('/')) return this.basePath + '/' + path;
    return this.basePath + path;
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
    let path = url.pathname;
    if (this.basePath && path.startsWith(this.basePath)) {
      path = path.slice(this.basePath.length) || '/';
    }
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

