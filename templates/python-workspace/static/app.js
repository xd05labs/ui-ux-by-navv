'use strict';
const $ = id => document.getElementById(id);
let config, user, csrf, records = [], editing = null, deleting = null, registering = false, requestSerial = 0;
const fields = new Map();
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500); }
async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...options.headers } });
  if (!response.ok) {
    const result = await response.json().catch(() => ({ error: 'Request failed' }));
    if (response.status === 401 && user) { user = null; $('workspace').hidden = true; $('auth').hidden = false; }
    throw new Error(result.error || `Request failed (${response.status})`);
  }
  return response;
}
async function json(path, options) { return (await api(path, options)).json(); }
function element(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node; }
function writable() { return !config.features.roleBasedAccess || user.role !== 'viewer'; }
function showError(error) { $('connection-message').textContent = navigator.onLine ? error.message : 'You are offline. Reconnect to sync your workspace.'; $('connection-error').hidden = false; }
function setup() {
  document.documentElement.lang = config.language;
  document.documentElement.dir = config.design.direction;
  document.body.dataset.layout = config.design.navigation.type;
  for (const node of document.querySelectorAll('.app-name')) node.textContent = config.name;
  document.title = config.name;
  $('objective').textContent = config.objective;
  $('records-nav').textContent = config.blueprint.collection;
  $('records-title').textContent = config.blueprint.collection;
  $('total-label').textContent = `Total ${config.blueprint.collection.toLowerCase()}`;
  $('complete-label').textContent = config.blueprint.statuses.at(-1);
  $('activity-nav').hidden = !config.features.auditLog;
  $('search-label').hidden = !config.features.search;
  $('export').hidden = !config.features.export;
  $('collapse').hidden = !config.design.navigation.collapsible || !['left-sidebar','floating-sidebar'].includes(config.design.navigation.type);
  $('auth-toggle').hidden = !config.registration;
  $('record-status').replaceChildren();
  $('filter-status').replaceChildren(new Option('All statuses', ''));
  for (const status of config.blueprint.statuses) { $('record-status').add(new Option(status, status)); $('filter-status').add(new Option(status, status)); }
  $('blueprint-fields').replaceChildren(); fields.clear();
  for (const field of config.blueprint.fields) {
    const label = element('label', field.label + (field.required ? ' *' : ''));
    const input = document.createElement('input'); input.id = `field-${field.name}`; input.type = field.type; input.required = field.required;
    if (field.type === 'number') { input.min = '0'; input.max = '1000000000000000'; input.step = 'any'; } else input.maxLength = 500;
    label.append(input); fields.set(field.name, { input, spec: field }); $('blueprint-fields').append(label);
  }
  $('command-links').replaceChildren();
  for (const link of document.querySelectorAll('nav[aria-label="Main navigation"] a')) { if (!link.hidden) { const copy = link.cloneNode(true); copy.removeAttribute('id'); copy.onclick = () => $('commands').close(); $('command-links').append(copy); } }
  let theme = config.design.theme;
  try { theme = localStorage.getItem('appforge-theme') || theme; } catch (_) { /* Storage may be disabled. */ }
  if (!['light','dark','system'].includes(theme)) theme = 'system';
  $('theme').value = theme; setTheme(theme);
}
function setTheme(theme) { if (theme === 'system') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; }
function route() {
  if (!config || !user) return;
  let page = location.hash.slice(1) || 'overview';
  if (!['overview','records','activity','settings'].includes(page) || (page === 'activity' && !config.features.auditLog)) page = 'overview';
  for (const section of document.querySelectorAll('[data-page]')) section.hidden = section.id !== page;
  for (const link of document.querySelectorAll('a[data-route]')) { if (link.dataset.route === page) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current'); }
  $('breadcrumb').textContent = `Workspace / ${page === 'records' ? config.blueprint.collection : page[0].toUpperCase() + page.slice(1)}`;
  if (page === 'activity') loadActivity().catch(showError);
}
async function boot() {
  try {
    const session = await json('/api/session'); config = { ...session.config, registration: session.registration }; user = session.user; csrf = session.csrf;
    setup(); $('boot').hidden = true; $('auth').hidden = !!user; $('workspace').hidden = !user;
    if (!user) return;
    $('account').textContent = user.role; $('account-email').textContent = user.email; $('account-role').textContent = user.role;
    for (const button of document.querySelectorAll('.create-record')) { button.hidden = !writable(); button.textContent = `Create ${config.blueprint.entity.toLowerCase()} +`; }
    route(); await Promise.all([loadRecords(), loadStats()]);
  } catch (error) {
    $('boot').hidden = false; $('boot').replaceChildren(element('p', error.message, 'error'));
    const retry = element('button', 'Retry'); retry.type = 'button'; retry.onclick = boot; $('boot').append(retry);
  }
}
async function loadStats() {
  const data = await json('/api/records'); const statuses = config.blueprint.statuses;
  $('total-count').textContent = data.total.toLocaleString();
  $('active-count').textContent = data.records.filter(row => row.status !== statuses.at(-1)).length.toLocaleString();
  $('complete-count').textContent = data.records.filter(row => row.status === statuses.at(-1)).length.toLocaleString();
  $('status-summary').replaceChildren();
  for (const status of statuses) { const count = data.records.filter(row => row.status === status).length; const line = element('p', `${status} · ${count} `); const meter = document.createElement('meter'); meter.min = 0; meter.max = Math.max(1, data.records.length); meter.value = count; meter.setAttribute('aria-label', `${status}: ${count} of ${data.records.length}`); line.append(meter); $('status-summary').append(line); }
}
async function loadRecords() {
  const serial = ++requestSerial;
  $('list-status').textContent = 'Loading records…'; $('record-table').setAttribute('aria-busy', 'true');
  try {
    const query = new URLSearchParams({ q: $('search').value, status: $('filter-status').value });
    const data = await json(`/api/records?${query}`);
    if (serial !== requestSerial) return;
    records = data.records; $('record-rows').replaceChildren();
    for (const record of records) {
      const tr = document.createElement('tr'); const title = element('td', record.title); const detail = element('div', record.description.slice(0, 100), 'muted'); title.append(detail);
      const status = document.createElement('td'); status.append(element('span', record.status, 'badge'));
      const updated = element('td', new Date(record.updated_at * 1000).toLocaleDateString()); const actions = document.createElement('td');
      const edit = element('button', writable() ? 'Edit' : 'View', 'secondary'); edit.type = 'button'; edit.setAttribute('aria-label', `${writable() ? 'Edit' : 'View'} ${record.title}`); edit.onclick = () => openRecord(record); actions.append(edit);
      if (writable()) { const remove = element('button', 'Delete', 'secondary'); remove.type = 'button'; remove.setAttribute('aria-label', `Delete ${record.title}`); remove.onclick = () => { deleting = record.id; $('delete-description').textContent = record.title; $('delete-dialog').showModal(); }; actions.append(document.createTextNode(' '), remove); }
      tr.append(title, status, updated, actions); $('record-rows').append(tr);
    }
    $('empty').hidden = records.length > 0; $('record-table').hidden = records.length === 0;
    $('list-status').textContent = `Showing ${records.length} matching records · ${data.total} total · latest ${data.limit} maximum`;
    $('connection-error').hidden = true;
  } catch (error) { $('list-status').textContent = 'Records could not be loaded.'; throw error; }
  finally { if (serial === requestSerial) $('record-table').removeAttribute('aria-busy'); }
}
function openRecord(record = null) {
  editing = record ? record.id : null;
  $('record-form').reset(); $('record-error').textContent = '';
  $('record-dialog-title').textContent = `${record ? (writable() ? 'Edit' : 'View') : 'Create'} ${config.blueprint.entity.toLowerCase()}`;
  $('record-title').value = record?.title || ''; $('record-description').value = record?.description || ''; $('record-status').value = record?.status || config.blueprint.statuses[0];
  for (const [name, field] of fields) field.input.value = record?.fields[name] ?? '';
  for (const input of $('record-form').querySelectorAll('input,textarea,select')) input.disabled = !writable();
  $('save-record').hidden = !writable(); $('record-dialog').showModal();
}
async function refresh() { await Promise.all([loadRecords(), loadStats()]); if (location.hash === '#activity' && config.features.auditLog) await loadActivity(); }
async function loadActivity() {
  const data = await json('/api/activity'); $('activity-list').replaceChildren();
  if (!data.events.length) $('activity-list').append(element('li', 'Your history starts with your first change.', 'muted'));
  for (const event of data.events) { const row = element('li', `${event.action[0].toUpperCase() + event.action.slice(1)} · ${event.title}`); row.append(element('div', new Date(event.created_at * 1000).toLocaleString(), 'muted')); $('activity-list').append(row); }
}
function setAuthMode(next) { registering = next; $('auth-title').textContent = registering ? 'A fresh start.' : 'Welcome back.'; $('auth-description').textContent = registering ? 'Create an account to begin.' : 'Sign in to your private workspace.'; $('auth-submit').textContent = registering ? 'Create account' : 'Sign in'; $('auth-toggle').textContent = registering ? 'Back to sign in' : 'Create an account'; $('password').autocomplete = registering ? 'new-password' : 'current-password'; $('auth-error').textContent = ''; }
$('auth-toggle').onclick = () => setAuthMode(!registering);
$('auth-form').onsubmit = async event => { event.preventDefault(); $('auth-submit').disabled = true; $('auth-error').textContent = ''; try { await json(registering ? '/api/register' : '/api/login', { method: 'POST', body: JSON.stringify({ email: $('email').value, password: $('password').value }) }); $('password').value = ''; await boot(); } catch (error) { $('auth-error').textContent = error.message; } finally { $('auth-submit').disabled = false; } };
$('logout').onclick = async () => { try { await json('/api/logout', { method: 'POST', body: '{}' }); user = null; csrf = null; records = []; setAuthMode(false); await boot(); } catch (error) { showError(error); } };
for (const button of document.querySelectorAll('.create-record')) button.onclick = () => openRecord();
$('cancel-record').onclick = () => $('record-dialog').close();
$('record-form').onsubmit = async event => { event.preventDefault(); $('save-record').disabled = true; $('record-error').textContent = ''; const values = {}; for (const [name, field] of fields) values[name] = field.spec.type === 'number' && field.input.value !== '' ? Number(field.input.value) : field.input.value;
  try { await json(editing ? `/api/records/${editing}` : '/api/records', { method: editing ? 'PUT' : 'POST', body: JSON.stringify({ title: $('record-title').value, description: $('record-description').value, status: $('record-status').value, fields: values }) }); $('record-dialog').close(); toast('Record saved.'); await refresh(); } catch (error) { $('record-error').textContent = error.message; } finally { $('save-record').disabled = false; } };
$('cancel-delete').onclick = () => $('delete-dialog').close();
$('confirm-delete').onclick = async () => { $('confirm-delete').disabled = true; try { await json(`/api/records/${deleting}`, { method: 'DELETE', body: '{}' }); $('delete-dialog').close(); toast('Record deleted.'); await refresh(); } catch (error) { $('delete-dialog').close(); showError(error); } finally { $('confirm-delete').disabled = false; } };
let searchTimer; $('search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => loadRecords().catch(showError), 180); };
$('filter-status').onchange = () => loadRecords().catch(showError);
$('export').onclick = async () => { try { const response = await api('/api/export'); const url = URL.createObjectURL(await response.blob()); const link = document.createElement('a'); link.href = url; link.download = 'records.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast('CSV exported.'); } catch (error) { showError(error); } };
$('theme').onchange = () => { setTheme($('theme').value); try { localStorage.setItem('appforge-theme', $('theme').value); } catch (_) { toast('Theme changed for this session.'); } };
$('collapse').onclick = () => { const collapsed = document.body.dataset.collapsed !== 'true'; document.body.dataset.collapsed = String(collapsed); $('collapse').setAttribute('aria-expanded', String(!collapsed)); };
$('command-open').onclick = () => $('commands').showModal(); $('command-close').onclick = () => $('commands').close();
document.addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && user) { event.preventDefault(); if (!$('commands').open) $('commands').showModal(); else $('commands').close(); } });
$('retry').onclick = () => refresh().catch(showError);
window.addEventListener('hashchange', route); window.addEventListener('offline', () => showError(new Error('You are offline.'))); window.addEventListener('online', () => { if (user) refresh().catch(showError); });
boot();
