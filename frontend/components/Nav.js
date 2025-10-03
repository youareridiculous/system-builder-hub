import { AppState } from "../app.js";

export function renderNav(container, resources) {
  if (!container) return;
  container.innerHTML = "";
  for (const r of resources) {
    const a = document.createElement('a');
    a.className = 'pill';
    a.href = AppState.router.to(`/r/${encodeURIComponent(r.name)}`);
    a.textContent = r.label || r.name;
    const current = location.pathname;
    const target = new URL(a.href, location.origin).pathname;
    if (current === target) {
      a.setAttribute('aria-current', 'page');
    }
    container.appendChild(a);
  }
}

