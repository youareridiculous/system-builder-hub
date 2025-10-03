import { AppState } from "../app.js";

function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'className') el.className = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v != null) el.setAttribute(k, String(v));
  }
  for (const c of children.flat()) {
    if (c == null) continue;
    if (typeof c === 'string') el.appendChild(document.createTextNode(c));
    else el.appendChild(c);
  }
  return el;
}

function buildToolbar({ resource, router }) {
  const q = new URL(location.href).searchParams;
  const searchInput = h('input', { type: 'text', placeholder: 'Search…', value: q.get('search') || '' });
  const limitSelect = h('select');
  [10, 20, 50, 100].forEach((n) => limitSelect.appendChild(h('option', { value: String(n), selected: (q.get('limit') || '20') === String(n) }, String(n))));
  const createBtn = h('a', { href: `/r/${encodeURIComponent(resource.name)}/new`, class: 'btn success' }, 'New');
  const applyBtn = h('button', { class: 'btn primary' }, 'Apply');

  applyBtn.addEventListener('click', () => {
    const params = new URLSearchParams(location.search);
    params.set('page', '1');
    params.set('limit', limitSelect.value);
    params.set('search', searchInput.value || '');
    router.replace(`${location.pathname}?${params.toString()}`);
  });

  return h('div', { class: 'toolbar' },
    h('div', { class: 'field', style: 'min-width:280px' }, searchInput),
    h('div', { class: 'field' }, limitSelect),
    h('div', { class: 'spacer' }),
    createBtn,
    applyBtn,
  );
}

function buildTable({ resource, rows, router }) {
  const urlParams = new URL(location.href).searchParams;
  const currentSort = urlParams.get('sort') || '';
  const currentOrder = (urlParams.get('order') || 'asc').toLowerCase() === 'desc' ? 'desc' : 'asc';

  const columns = resource.columns || Object.keys(rows[0] || {} ).map((k) => ({ key: k, label: k }));
  const ths = columns.map((c) => {
    const isActive = currentSort === c.key;
    const nextOrder = isActive && currentOrder === 'asc' ? 'desc' : 'asc';
    const indicator = isActive ? (currentOrder === 'asc' ? ' ▲' : ' ▼') : '';
    const btn = h('button', { class: 'btn', type: 'button' }, (c.label || c.key) + indicator);
    btn.addEventListener('click', () => {
      const params = new URLSearchParams(location.search);
      params.set('sort', c.key);
      params.set('order', nextOrder);
      params.set('page', '1');
      router.replace(`${location.pathname}?${params.toString()}`);
    });
    return h('th', {}, btn);
  });
  const thead = h('thead', {}, h('tr', {}, ...ths, h('th', {}, 'Actions')));
  const tbody = h('tbody');

  for (const row of rows) {
    const idKey = resource.idKey || 'id';
    const id = row[idKey];
    const editHref = `/r/${encodeURIComponent(resource.name)}/${encodeURIComponent(id)}/edit`;
    const editBtn = h('a', { href: editHref, class: 'btn' }, 'Edit');
    const delBtn = h('button', { class: 'btn danger' }, 'Delete');
    delBtn.addEventListener('click', async () => {
      if (!confirm('Delete this record?')) return;
      await AppState.apiClient.delete(resource.name, id);
      router.replace(location.pathname + location.search);
    });

    const tds = columns.map((c) => h('td', {}, String(row[c.key])));
    tds.push(h('td', { class: 'row-actions' }, editBtn, delBtn));
    tbody.appendChild(h('tr', {}, ...tds));
  }

  return h('table', { class: 'table' }, thead, tbody);
}

function buildPagination({ page, total, limit, router }) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(1, limit)));
  const prev = h('button', { class: 'btn', disabled: page <= 1 ? '' : null }, 'Prev');
  const next = h('button', { class: 'btn', disabled: page >= totalPages ? '' : null }, 'Next');
  const label = h('span', {}, `Page ${page} of ${totalPages}`);

  function setPage(p) {
    const params = new URLSearchParams(location.search);
    params.set('page', String(p));
    history.replaceState({}, '', `${location.pathname}?${params.toString()}`);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  prev.addEventListener('click', () => page > 1 && setPage(page - 1));
  next.addEventListener('click', () => page < totalPages && setPage(page + 1));

  return h('div', { class: 'pagination' }, prev, label, next);
}

export async function renderListView({ mount, resource, apiClient, config, query }) {
  mount.innerHTML = '';
  const page = Number(query.page || 1);
  const limit = Number(query.limit || 20);
  const search = query.search || '';
  const sort = query.sort || '';
  const order = (query.order || 'asc');

  const card = h('div', { class: 'card' });
  const header = h('div', { class: 'card-header' },
    h('div', {}, resource.label || resource.name),
    buildToolbar({ resource, router: AppState.router }),
  );
  const body = h('div', { class: 'card-body' }, 'Loading…');
  card.append(header, body);
  mount.append(card);

  const response = await apiClient.list(resource.name, { page, limit, search, sort, order });
  const rows = Array.isArray(response.items) ? response.items : (Array.isArray(response) ? response : []);
  const total = typeof response.total === 'number' ? response.total : rows.length;

  body.innerHTML = '';
  if (rows.length === 0) {
    body.append(h('div', {}, 'No results'));
  } else {
    body.append(buildTable({ resource, rows, router: AppState.router }));
  }
  body.append(h('div', { style: 'margin-top:12px' }, buildPagination({ page, total, limit, router: AppState.router })));
}

