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

function renderField(field, value) {
  const id = `f_${field.name}`;
  const label = h('label', { for: id }, field.label || field.name);
  let input;
  const base = { id, name: field.name };
  switch (field.type) {
    case 'number': input = h('input', { ...base, type: 'number', value: value ?? '' }); break;
    case 'date': input = h('input', { ...base, type: 'date', value: value ?? '' }); break;
    case 'select': {
      input = h('select', base);
      (field.options || []).forEach((opt) => input.appendChild(h('option', { value: String(opt.value), selected: String(value ?? '') === String(opt.value) ? '' : null }, String(opt.label))));
      break;
    }
    case 'textarea': input = h('textarea', base, String(value ?? '')); break;
    default: input = h('input', { ...base, type: 'text', value: value ?? '' });
  }
  const wrap = h('div', { class: 'field' }, label, input, h('div', { class: 'error', id: `${id}_err` }));
  return { wrap, input };
}

function validate(fields, formEl) {
  let ok = true;
  for (const f of fields) {
    const input = formEl.querySelector(`[name="${CSS.escape(f.name)}"]`);
    const errEl = formEl.querySelector(`#f_${CSS.escape(f.name)}_err`);
    let err = '';
    if (f.required && !input.value) err = 'Required';
    if (f.minLength && input.value && input.value.length < f.minLength) err = `Min ${f.minLength} chars`;
    if (f.maxLength && input.value && input.value.length > f.maxLength) err = `Max ${f.maxLength} chars`;
    errEl.textContent = err;
    if (err) ok = false;
  }
  return ok;
}

export async function renderFormView({ mount, resource, apiClient, mode, id }) {
  mount.innerHTML = '';
  const card = h('div', { class: 'card' });
  const header = h('div', { class: 'card-header' }, `${mode === 'create' ? 'Create' : 'Edit'} ${resource.label || resource.name}`);
  const body = h('div', { class: 'card-body' }, 'Loading…');
  card.append(header, body);
  mount.append(card);

  let existing = null;
  if (mode === 'edit') {
    existing = await apiClient.get(resource.name, id);
  }

  const form = h('form');
  const fields = resource.fields || (resource.columns || []).map((c) => ({ name: c.key || c.name || c, label: c.label || c.key || c, type: 'text' }));
  const values = existing || {};
  const inputs = [];
  for (const f of fields) {
    if (f.name === (resource.idKey || 'id')) continue;
    const { wrap, input } = renderField(f, values[f.name]);
    form.append(wrap);
    inputs.push({ field: f, input });
  }

  const submit = h('button', { class: 'btn primary', type: 'submit' }, mode === 'create' ? 'Create' : 'Save changes');
  const cancel = h('a', { href: AppState.router.to(`/r/${encodeURIComponent(resource.name)}`), class: 'btn' }, 'Cancel');
  form.append(h('div', { class: 'toolbar' }, submit, cancel));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validate(fields, form)) return;
    const payload = {};
    for (const { field, input } of inputs) {
      let v = input.value;
      if (field.type === 'number' && v !== '') v = Number(v);
      payload[field.name] = v;
    }
    if (mode === 'create') await apiClient.create(resource.name, payload);
    else await apiClient.update(resource.name, id, payload);
    AppState.router.replace(`/r/${encodeURIComponent(resource.name)}`);
  });

  body.innerHTML = '';
  body.append(form);
}

