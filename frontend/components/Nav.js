import { AppState } from "../app.js";

export function renderNav(container, resources) {
  if (!container) return;
  container.innerHTML = "";
  for (const r of resources) {
    const a = document.createElement('a');
    a.className = 'pill';
    a.href = `/r/${encodeURIComponent(r.name)}`;
    a.textContent = r.label || r.name;
    if (location.pathname === a.getAttribute('href')) {
      a.setAttribute('aria-current', 'page');
    }
    container.appendChild(a);
  }
}

