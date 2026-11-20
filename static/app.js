/* XingfaCAD - GUI nhập liệu (vanilla JS, không cần build step) */
const state = {
  status: null,
  systems: [],
  system: null,
  project: null,
  catalog: null,
  pricing: null,
  result: null,
  imageData: null,
  previewTab: 'preview',
  selectedTag: null,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const nf = new Intl.NumberFormat('vi-VN');

const money = (v) => nf.format(Math.round(Number(v) || 0));
const num = (v, digits = 0) => (Number(v) || 0).toLocaleString('vi-VN', { maximumFractionDigits: digits });

async function api(path, options = {}) {
  const config = { headers: { 'Content-Type': 'application/json' }, ...options };
  if (config.body && typeof config.body !== 'string') config.body = JSON.stringify(config.body);
  const res = await fetch(path, config);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch (err) { /* ignore */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

let toastTimer = null;
function toast(message, isError = false) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.toggle('error', isError);
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 4200);
}

function setStatus(message, kind = '') {
  const el = $('#build-status');
  el.textContent = message;
  el.className = `build-status ${kind}`;
}

/* ---------------- tabs ---------------- */
function initTabs() {
  $$('#main-tabs .tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('#main-tabs .tab').forEach((b) => b.classList.toggle('active', b === btn));
      $$('.tab-panel').forEach((panel) => panel.classList.toggle('active', panel.id === `tab-${btn.dataset.tab}`));
    });
  });
}

/* ---------------- dữ liệu cơ bản ---------------- */
function glassByKey(key) {
  const glass = state.catalog?.glass?.[key];
  if (glass) return { key, name: glass.name, thickness_mm: glass.thickness_mm, price_per_m2: glass.price_per_m2 };
  return { key, name: key, thickness_mm: 8, price_per_m2: 0 };
}

function defaultProject() {
  const system = state.systems[0]?.code || 'XF65';
  const glassKey = Object.keys(state.catalog?.glass || {})[0] || 'cuong_luc_8';
  const today = new Date().toISOString().slice(0, 10);
  return {
    project: {
      code: `DU-AN-${new Date().getFullYear()}`,
      name: '',
      customer: '',
      address: '',
      date: today,
      currency: 'VND',
    },
    defaults: { system, glass: glassByKey(glassKey), color: 'Trắng sứ', hardware: 'Kinlong' },
    items: [],
  };
}

const DIRS = {
  l: 'left', left: 'left', trai: 'left', 'trái': 'left',
  r: 'right', right: 'right', phai: 'right', 'phải': 'right',
  u: 'up', up: 'up', tren: 'up', 'trên': 'up',
  d: 'down', down: 'down', duoi: 'down', 'dưới': 'down',
  s: 'none', slide: 'none', lua: 'none', 'lùa': 'none', none: 'none',
};

const FIXED_WORDS = ['fixed', 'fix', 'f', 'cd', 'codinh', 'cốđịnh', 'cố định', 'kinh', 'kính'];

function textToPanels(text, type) {
  if (!text || !text.trim()) return [];
  const sliding = type === 'sliding' || type === 'door_sliding';
  return text.split(',').map((segment) => {
    const tokens = segment.split(':').map((t) => t.trim()).filter(Boolean);
    if (!tokens.length) return null;
    const first = tokens[0].toLowerCase().replace(/\s+/g, '');
    const kind = FIXED_WORDS.includes(first) ? 'fixed' : 'sash';
    const panel = {
      kind,
      open: kind === 'fixed' ? 'none' : (sliding ? 'slide' : 'out'),
      dir: kind === 'fixed' || sliding ? 'none' : 'left',
      ratio: 1,
    };
    tokens.slice(1).forEach((token) => {
      const low = token.toLowerCase();
      if (/^[0-9]+(\.[0-9]+)?$/.test(low)) { panel.ratio = parseFloat(low); return; }
      if (low === 'slide' || low === 'lua' || low === 'lùa' || low === 's') { panel.open = 'slide'; panel.dir = 'none'; return; }
      const dir = DIRS[low] || DIRS[low[0]];
      if (dir) panel.dir = dir;
    });
    return panel;
  }).filter(Boolean);
}

function panelsToText(panels) {
  return (panels || []).map((p) => {
    const parts = [p.kind === 'fixed' ? 'fixed' : 'sash'];
    if (p.open === 'slide') parts.push('slide');
    else if (p.dir && p.dir !== 'none') parts.push(p.dir[0].toUpperCase());
    if (p.ratio && p.ratio !== 1) parts.push(String(p.ratio));
    return parts.join(':');
  }).join(', ');
}

function textToTransoms(text) {
  if (!text || !text.trim()) return [];
  return text.split(';').map((segment) => {
    const raw = segment.trim();
    if (!raw) return null;
    const [head, band] = raw.split(':');
    const clean = head.trim().toLowerCase();
    const orientation = clean.startsWith('v') ? 'v' : 'h';
    const at = parseFloat(clean.replace(/^[a-z]/, '').replace('@', ''));
    if (!at || at <= 0) return null;
    const transom = { orientation, at_mm: at, profile: 'transom' };
    const kind = (band || '').trim();
    if (kind === 'fixed' || kind === 'sash') transom.band_above = kind;
    return transom;
  }).filter(Boolean);
}

function transomsToText(transoms) {
  return (transoms || []).map((t) => {
    let text = `${t.orientation || 'h'}@${Math.round(t.at_mm)}`;
    if (t.band_above) text += `:${t.band_above}`;
    return text;
  }).join('; ');
}

function emptyItem(index) {
  const system = state.project?.defaults?.system || state.systems[0]?.code || 'XF65';
  return {
    tag: `C${index + 1}`,
    room: '',
    qty: 1,
    type: 'casement',
    width_mm: 1200,
    height_mm: 1500,
    sill_mm: 900,
    system,
    panels: [],
    transoms: [],
    notes: '',
    glass: { ...(state.project?.defaults?.glass || glassByKey('cuong_luc_8')) },
  };
}

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

function fillSystemSelect(select, value) {
  select.innerHTML = state.systems
    .map((s) => `<option value="${escapeHtml(s.code)}"${s.code === value ? ' selected' : ''}>${escapeHtml(s.code)} - ${escapeHtml(s.name)}</option>`)
    .join('');
}

function fillGlassSelect(select, value) {
  const glass = state.catalog?.glass || {};
  select.innerHTML = Object.entries(glass)
    .map(([key, g]) => `<option value="${escapeHtml(key)}"${key === value ? ' selected' : ''}>${escapeHtml(g.name)} (${money(g.price_per_m2)} đ/m²)</option>`)
    .join('');
}

function saveLocal() {
  try { localStorage.setItem('xfcad.project', JSON.stringify(state.project)); } catch (err) { /* ignore */ }
}

function switchTab(name) {
  $$('#main-tabs .tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
  $$('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === `tab-${name}`));
}

function renderProject() {
  const project = state.project;
  $('#p-code').value = project.project.code || '';
  $('#p-name').value = project.project.name || '';
  $('#p-customer').value = project.project.customer || '';
  $('#p-address').value = project.project.address || '';
  $('#p-date').value = project.project.date || '';
  $('#p-color').value = project.defaults.color || '';
  $('#p-hardware').value = project.defaults.hardware || '';
  fillSystemSelect($('#p-system'), project.defaults.system);
  fillGlassSelect($('#p-glass'), project.defaults.glass?.key);
  renderItems();
}

function renderItems() {
  const tbody = $('#items-body');
  const items = state.project.items;
  $('#item-count').textContent = items.length;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="13" style="text-align:center;color:#64748b;padding:26px">
      Chưa có cửa nào. Bấm <b>+ Thêm cửa</b> hoặc <b>Dự án mẫu</b>.</td></tr>`;
    return;
  }
  const typeOptions = Object.entries(state.status?.item_types || {});
  const rowHtml = (item, index) => {
    const typeOpts = typeOptions.map(([value, label]) =>
      `<option value="${value}"${item.type === value ? ' selected' : ''}>${escapeHtml(label)}</option>`).join('');
    const sysOpts = state.systems.map((s) =>
      `<option value="${escapeHtml(s.code)}"${(item.system || state.project.defaults.system) === s.code ? ' selected' : ''}>${escapeHtml(s.code)}</option>`).join('');
    const glassOpts = Object.entries(state.catalog?.glass || {}).map(([key, g]) =>
      `<option value="${escapeHtml(key)}"${item.glass?.key === key ? ' selected' : ''}>${escapeHtml(g.name)}</option>`).join('');
    return `<tr data-index="${index}">
      <td><input data-field="tag" value="${escapeHtml(item.tag)}" /></td>
      <td><input data-field="room" value="${escapeHtml(item.room)}" placeholder="Phòng khách" /></td>
      <td><select data-field="type">${typeOpts}</select></td>
      <td><select data-field="system">${sysOpts}</select></td>
      <td><input data-field="width_mm" type="number" min="100" step="10" value="${item.width_mm}" /></td>
      <td><input data-field="height_mm" type="number" min="100" step="10" value="${item.height_mm}" /></td>
      <td><input data-field="qty" type="number" min="1" step="1" value="${item.qty}" /></td>
      <td><input data-field="sill_mm" type="number" min="0" step="50" value="${item.sill_mm}" /></td>
      <td><input data-field="panels" value="${escapeHtml(panelsToText(item.panels))}" placeholder="tự động" /></td>
      <td><input data-field="transoms" value="${escapeHtml(transomsToText(item.transoms))}" placeholder="h@500:fixed" /></td>
      <td><select data-field="glass">${glassOpts}</select></td>
      <td><input data-field="notes" value="${escapeHtml(item.notes)}" placeholder="Ghi chú" /></td>
      <td><button class="icon-btn" data-action="del" title="Xóa">✕</button></td>
    </tr>`;
  };
  tbody.innerHTML = items.map(rowHtml).join('');
}

function bindProject() {
  const headerMap = {
    'p-code': (v) => { state.project.project.code = v.trim(); },
    'p-name': (v) => { state.project.project.name = v; },
    'p-customer': (v) => { state.project.project.customer = v; },
    'p-address': (v) => { state.project.project.address = v; },
    'p-date': (v) => { state.project.project.date = v; },
    'p-color': (v) => { state.project.defaults.color = v; },
    'p-hardware': (v) => { state.project.defaults.hardware = v; },
  };
  Object.entries(headerMap).forEach(([id, apply]) => {
    $(`#${id}`).addEventListener('input', (e) => { apply(e.target.value); saveLocal(); });
  });
  $('#p-system').addEventListener('change', (e) => {
    state.project.defaults.system = e.target.value;
    state.project.items.forEach((item) => { item.system = e.target.value; });
    renderItems();
    saveLocal();
  });
  $('#p-glass').addEventListener('change', (e) => {
    state.project.defaults.glass = glassByKey(e.target.value);
    state.project.items.forEach((item) => { item.glass = { ...state.project.defaults.glass }; });
    renderItems();
    saveLocal();
  });

  $('#items-body').addEventListener('input', (e) => {
    const row = e.target.closest('tr');
    const field = e.target.dataset.field;
    if (!row || !field) return;
    const item = state.project.items[Number(row.dataset.index)];
    if (!item) return;
    const raw = e.target.value;
    if (field === 'width_mm' || field === 'height_mm' || field === 'qty' || field === 'sill_mm') {
      item[field] = Number(raw) || 0;
    } else if (field === 'panels') {
      item.panels = textToPanels(raw, item.type);
    } else if (field === 'transoms') {
      item.transoms = textToTransoms(raw);
    } else if (field === 'glass') {
      item.glass = glassByKey(raw);
    } else if (field === 'tag') {
      item.tag = raw.trim();
    } else {
      item[field] = raw;
    }
    saveLocal();
  });

  $('#items-body').addEventListener('change', (e) => {
    if (e.target.dataset.field !== 'type') return;
    const row = e.target.closest('tr');
    const item = state.project.items[Number(row.dataset.index)];
    item.type = e.target.value;
    const sliding = item.type === 'sliding' || item.type === 'door_sliding';
    item.panels = (item.panels || []).map((p) => ({
      ...p,
      open: sliding ? 'slide' : (p.kind === 'fixed' ? 'none' : 'out'),
      dir: sliding || p.kind === 'fixed' ? 'none' : p.dir,
    }));
    renderItems();
    saveLocal();
  });

  $('#items-body').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action="del"]');
    if (!btn) return;
    const row = btn.closest('tr');
    state.project.items.splice(Number(row.dataset.index), 1);
    renderItems();
    saveLocal();
  });

  $('#btn-add-item').addEventListener('click', () => {
    state.project.items.push(emptyItem(state.project.items.length));
    renderItems();
    saveLocal();
  });

  $('#btn-dup-item').addEventListener('click', () => {
    const items = state.project.items;
    if (!items.length) return;
    const clone = JSON.parse(JSON.stringify(items[items.length - 1]));
    const existing = new Set(items.map((i) => i.tag));
    let index = items.length + 1;
    while (existing.has(`C${index}`)) index += 1;
    clone.tag = `C${index}`;
    items.push(clone);
    renderItems();
    saveLocal();
  });

  $('#btn-demo').addEventListener('click', async () => {
    try {
      const demo = await api('/api/demo');
      state.project = demo;
      renderProject();
      saveLocal();
      toast('Đã nạp dự án mẫu');
    } catch (err) { toast(err.message, true); }
  });

  $('#btn-export-json').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(collectProject(), null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${state.project.project.code || 'du-an'}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  });

  $('#file-json').addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      state.project = normalizeProject(data);
      renderProject();
      saveLocal();
      toast('Đã mở file JSON');
    } catch (err) { toast(`JSON không hợp lệ: ${err.message}`, true); }
    e.target.value = '';
  });

  $('#btn-reset').addEventListener('click', () => {
    if (!confirm('Xóa toàn bộ dữ liệu đang nhập và bắt đầu mới?')) return;
    state.project = defaultProject();
    renderProject();
    saveLocal();
    toast('Đã làm mới');
  });

  $('#btn-validate').addEventListener('click', doValidate);
  $('#btn-build').addEventListener('click', doBuild);
}

function normalizeProject(raw) {
  const base = defaultProject();
  const items = raw.items || raw.data?.items || [];
  return {
    project: { ...base.project, ...(raw.project || {}) },
    defaults: { ...base.defaults, ...(raw.defaults || {}) },
    items: items.map((item, index) => ({
      tag: item.tag || `C${index + 1}`,
      room: item.room || '',
      qty: item.qty || 1,
      type: item.type || 'casement',
      width_mm: Number(item.width_mm) || 1200,
      height_mm: Number(item.height_mm) || 1500,
      sill_mm: item.sill_mm ?? 900,
      system: item.system || null,
      panels: item.panels || [],
      transoms: item.transoms || [],
      glass: item.glass?.key ? glassByKey(item.glass.key) : { ...base.defaults.glass },
      notes: item.notes || '',
      source: item.source || 'manual',
      confidence: item.confidence ?? 1,
      needs_review: item.needs_review || [],
    })),
  };
}

function collectProject() {
  const project = JSON.parse(JSON.stringify(state.project));
  project.project.code = (project.project.code || 'DU-AN').trim();
  project.items.forEach((item, index) => {
    if (!item.tag) item.tag = `C${index + 1}`;
    item.system = item.system || project.defaults.system;
    item.glass = item.glass?.key ? glassByKey(item.glass.key) : { ...project.defaults.glass };
    item.panels = item.panels || [];
    item.transoms = item.transoms || [];
  });
  return project;
}

function ensureValidatePanel() {
  let panel = $('#validate-panel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'validate-panel';
    panel.className = 'card';
    panel.hidden = true;
    const section = $('#tab-project');
    section.insertBefore(panel, section.querySelector('.sticky-actions'));
  }
  return panel;
}

function showIssues(issues, title = 'Kết quả kiểm tra') {
  const panel = ensureValidatePanel();
  panel.hidden = false;
  const rows = (issues || []).map((issue) => {
    const level = issue.level || 'warning';
    return `<li class="${level}"><b>${level === 'error' ? 'LỖI' : level === 'warning' ? 'CẢNH BÁO' : 'INFO'}</b>
      ${issue.tag ? `[${escapeHtml(issue.tag)}] ` : ''}${escapeHtml(issue.message)}</li>`;
  }).join('');
  panel.innerHTML = `<h2>${escapeHtml(title)}</h2>
    <ul class="issues">${rows || '<li class="info">Không có vấn đề gì.</li>'}</ul>`;
}

async function doValidate() {
  setStatus('Đang kiểm tra...');
  try {
    const result = await api('/api/validate', { method: 'POST', body: collectProject() });
    const errors = (result.issues || []).filter((i) => i.level === 'error').length;
    showIssues(result.issues, result.ok ? 'Dữ liệu hợp lệ' : `Có ${errors} lỗi cần sửa`);
    if (result.ok) {
      setStatus(`Hợp lệ: ${result.totals.items} cửa | ${num(result.totals.area_m2, 2)} m² | ${num(result.totals.alum_kg, 2)} kg nhôm`, 'ok');
      toast('Dữ liệu hợp lệ');
    } else {
      setStatus(`${errors} lỗi - xem chi tiết bên dưới bảng`, 'error');
      toast(`Có ${errors} lỗi cần sửa`, true);
    }
  } catch (err) {
    setStatus(err.message, 'error');
    toast(err.message, true);
  }
}

async function doBuild() {
  const button = $('#btn-build');
  button.disabled = true;
  setStatus('Đang build... (gọi FreeCAD có thể mất 10-60 giây)', '');
  try {
    const outcome = await api('/api/build', {
      method: 'POST',
      body: { project: collectProject(), with_3d: $('#opt-3d').checked, with_drawings: true },
    });
    state.result = outcome;
    state.selectedTag = outcome.items[0]?.tag || null;
    state.previewTab = 'preview';
    renderResult(outcome);
    switchTab('result');
    const freecadInfo = outcome.freecad || {};
    const note = outcome.freecad?.ok ? 'FreeCAD OK' : '3D: xem ghi chú FreeCAD';
    setStatus(`Xong: ${outcome.artifacts.length} file | ${note}`, 'ok');
    toast(`Build xong ${outcome.artifacts.length} file`);
  } catch (err) {
    setStatus(err.message, 'error');
    toast(err.message, true);
    try {
      const detail = JSON.parse(err.message);
      if (detail?.issues) showIssues(detail.issues, 'Không build được');
    } catch (parseErr) { /* ignore */ }
  } finally {
    button.disabled = false;
  }
}

function metric(label, value, unit = '', accent = false) {
  return `<div class="metric${accent ? ' accent' : ''}">
    <div class="label">${escapeHtml(label)}</div>
    <div class="value">${value}${unit ? `<span class="unit">${escapeHtml(unit)}</span>` : ''}</div>
  </div>`;
}

function fileLinks(files) {
  if (!files) return '';
  const items = [];
  if (files.dxf) items.push(`<a class="artifact" href="${files.dxf}" download title="Bản vẽ DXF"><span class="kind">DXF</span></a>`);
  if (files.drawing) items.push(`<a class="artifact" href="${files.drawing}" target="_blank" title="Bản vẽ 2D"><span class="kind">2D</span></a>`);
  if (files.preview) items.push(`<a class="artifact" href="${files.preview}" target="_blank" title="Ảnh 3D"><span class="kind">3D</span></a>`);
  if (files.obj) items.push(`<a class="artifact" href="${files.obj}" download title="Mô hình OBJ"><span class="kind">OBJ</span></a>`);
  return items.join(' ');
}

function renderResult(outcome) {
  $('#result-empty').hidden = true;
  $('#result-content').hidden = false;
  const s = outcome.summary || {};
  $('#summary-cards').innerHTML = [
    metric('Hạng mục', s.items ?? 0),
    metric('Diện tích', num(s.area_m2, 2), 'm²'),
    metric('Nhôm', num(s.alum_kg, 1), 'kg'),
    metric('Kính', num(s.glass_m2, 1), 'm²'),
    metric('Giá vốn', money(s.cost_total), 'đ'),
    metric('Doanh thu', money(s.price), 'đ'),
    metric('VAT', money(s.vat), 'đ'),
    metric('Tổng thanh toán', money(s.price_with_vat), 'đ', true),
  ].join('');

  const head = `<thead><tr><th>Mã</th><th>Loại cửa</th><th>Hệ</th><th>R × C</th><th>SL</th>
    <th>DT (m²)</th><th>Nhôm (kg)</th><th>Kính (m²)</th><th>Giá bán</th><th>File</th></tr></thead>`;
  const body = (outcome.items || []).map((item) => `<tr>
    <td><b>${escapeHtml(item.tag)}</b></td>
    <td>${escapeHtml(item.type_label)}</td>
    <td>${escapeHtml(item.system)}</td>
    <td>${item.width_mm} × ${item.height_mm}</td>
    <td class="num">${item.qty}</td>
    <td class="num">${num(item.area_m2, 2)}</td>
    <td class="num">${num(item.alum_kg, 2)}</td>
    <td class="num">${num(item.glass_m2, 2)}</td>
    <td class="num">${money(item.price)}</td>
    <td>${fileLinks(item.files)}</td>
  </tr>`).join('');
  $('#result-table').innerHTML = head + `<tbody>${body}</tbody>`;

  renderPreview();
  renderResultIssues(outcome.issues || []);
  renderFreecad(outcome.freecad || {}, s);
  renderCutPlan(outcome.cut_plan || []);
  renderArtifacts(outcome.artifacts || []);
}

function renderPreview() {
  const items = state.result?.items || [];
  if (!items.length) return;
  const active = items.find((i) => i.tag === state.selectedTag) || items[0];
  state.selectedTag = active.tag;
  const tabs = items.map((item) =>
    `<button class="tab${item.tag === active.tag ? ' active' : ''}" data-tag="${escapeHtml(item.tag)}">${escapeHtml(item.tag)}</button>`).join('');
  const views = `<button class="tab${state.previewTab === 'preview' ? ' active' : ''}" data-view="preview">3D</button>
    <button class="tab${state.previewTab === 'drawing' ? ' active' : ''}" data-view="drawing">Bản vẽ</button>`;
  $('#preview-tabs').innerHTML = `${tabs}<span style="flex:1"></span>${views}`;
  const url = state.previewTab === 'drawing' ? active.files?.drawing : active.files?.preview;
  $('#preview-box').innerHTML = url
    ? `<img src="${url}" alt="${escapeHtml(active.tag)}" />`
    : 'Hạng mục này chưa có file xem trước';
}

function renderResultIssues(issues) {
  const rows = issues.map((issue) => {
    const level = issue.level || 'warning';
    return `<li class="${level}">${issue.tag ? `[${escapeHtml(issue.tag)}] ` : ''}${escapeHtml(issue.message)}</li>`;
  }).join('');
  $('#issue-list').innerHTML = rows || '<li class="info">Không có cảnh báo.</li>';
}

function renderFreecad(info, summary) {
  const box = $('#freecad-box');
  if (!info || Object.keys(info).length === 0) {
    box.innerHTML = '<p>Chưa gọi FreeCAD.</p>';
    return;
  }
  const available = info.available ? '<span class="tag ok">đã cài</span>' : '<span class="tag warn">chưa cài</span>';
  const status = info.ok ? '<span class="tag ok">xuất 3D OK</span>' : '<span class="tag warn">chưa xuất 3D</span>';
  let detail = '';
  if (info.report) {
    detail = `<p>Objects: <b>${info.report.objects ?? 0}</b> | Thể tích: <b>${num(info.report.total_volume_mm3, 0)}</b> mm³</p>`;
  }
  if (info.message) detail += `<p>${escapeHtml(info.message)}</p>`;
  if (info.path) detail += `<p>FreeCADCmd: <code>${escapeHtml(info.path)}</code></p>`;
  if (summary?.bars) detail += `<p>Số cây nhôm: <b>${summary.bars}</b> | phế: <b>${num(summary.waste_m, 2)} m</b></p>`;
  box.innerHTML = `<p>FreeCAD ${available} ${status}</p>${detail}`;
}

function renderCutPlan(groups) {
  if (!groups.length) {
    $('#cut-box').innerHTML = '<p>Không có dữ liệu cắt.</p>';
    return;
  }
  const totalBars = groups.reduce((acc, g) => acc + (g.bars || 0), 0);
  const totalWaste = groups.reduce((acc, g) => acc + (g.waste_m || 0), 0);
  const html = groups.map((group) => `<div style="margin-bottom:8px">
      <b>${escapeHtml(group.profile_code)}</b> - ${escapeHtml(group.profile_name)} |
      ${group.bars} cây × ${group.stock_mm} mm | phế ${num(group.waste_m, 2)} m (${num(group.waste_percent, 1)}%)
      ${group.patterns.slice(0, 4).map((p) => `<div class="cut-line">${escapeHtml(p)}</div>`).join('')}
      ${group.patterns.length > 4 ? `<div class="cut-line">... +${group.patterns.length - 4} cây</div>` : ''}
    </div>`).join('');
  $('#cut-box').innerHTML = `<p><b>${totalBars}</b> cây | tổng phế <b>${num(totalWaste, 2)}</b> m</p>${html}`;
}

function renderArtifacts(artifacts) {
  $('#artifact-list').innerHTML = artifacts.map((file) => `<a class="artifact" href="${file.url}" download>
      <span class="kind">${escapeHtml(file.kind)}</span>${escapeHtml(file.name)}
      <span class="size">${num((file.size || 0) / 1024, 1)} KB</span>
    </a>`).join('');
}

/* ---------------- catalogue hệ nhôm ---------------- */
const RULE_FIELDS = [
  ['gap_frame_sash_mm', 'Khe khung - cánh (mm)'],
  ['sash_overlap_mm', 'Cánh chồng khi lùa (mm)'],
  ['glass_rebate_mm', 'Ngậm kính vào rãnh (mm)'],
  ['glass_clearance_mm', 'Khe hở lắp kính (mm)'],
  ['min_panel_width_mm', 'Cánh rộng tối thiểu (mm)'],
  ['max_panel_area_m2', 'Diện tích ô tối đa (m²)'],
  ['track_offset_mm', 'Lệch ray lùa (mm)'],
  ['sash_inset_mm', 'Cánh thụt vào (mm, trống = tự tính)'],
];

const PROFILE_KEYS = [
  ['frame', 'Khung bao'], ['sash', 'Cánh'], ['mullion', 'Đố đứng'],
  ['transom', 'Đố ngang'], ['track_top', 'Ray trên'], ['track_bottom', 'Ray dưới'], ['bead', 'Nẹp kính'],
];

function renderSystemList() {
  const active = state.system?.code;
  $('#system-list').innerHTML = state.systems.map((system) => `
    <li data-code="${escapeHtml(system.code)}" class="${system.code === active ? 'active' : ''}">
      <div>
        <div class="code">${escapeHtml(system.code)}</div>
        <div class="sub">${escapeHtml(system.name)}</div>
      </div>
      <span class="tag ${system.verified ? 'ok' : 'warn'}">${system.verified ? 'đã xác nhận' : 'chưa xác nhận'}</span>
    </li>`).join('') || '<li class="sub">Chưa có hệ nhôm</li>';
}

async function loadSystems() {
  state.systems = await api('/api/systems');
  renderSystemList();
}

async function openSystem(code) {
  try {
    state.system = await api(`/api/systems/${encodeURIComponent(code)}`);
    renderSystem();
    renderSystemList();
    fillSystemSelect($('#p-system'), state.project.defaults.system);
  } catch (err) { toast(err.message, true); }
}

function renderSystem() {
  const system = state.system;
  if (!system) return;
  $('#system-title').textContent = `${system.code} - ${system.name}`;
  $('#s-code').value = system.code || '';
  $('#s-name').value = system.name || '';
  $('#s-kind').value = system.kind || 'casement';
  $('#s-joint').value = system.joint || 'miter45';
  $('#s-bar').value = system.bar_length_mm ?? 6500;
  $('#s-kerf').value = system.kerf_mm ?? 5;
  $('#s-trim').value = system.end_trim_mm ?? 30;
  $('#s-verified').checked = Boolean(system.verified);
  $('#s-source').value = system.source || '';
  $('#s-notes').value = system.notes || '';
  const rules = system.rules || {};
  $('#rules-grid').innerHTML = RULE_FIELDS.map(([key, label]) => {
    const value = rules[key];
    return `<label>${escapeHtml(label)}<input id="rule-${key}" type="number" step="0.5"
      value="${value === null || value === undefined ? '' : value}" /></label>`;
  }).join('');
  renderProfiles();
}

function renderProfiles() {
  const profiles = state.system?.profiles || {};
  const rows = Object.entries(profiles).map(([key, profile]) => profileRow(key, profile)).join('');
  $('#profiles-body').innerHTML = rows || '';
}

function profileRow(key, profile = {}) {
  const options = PROFILE_KEYS.map(([value, label]) =>
    `<option value="${value}"${value === key ? ' selected' : ''}>${escapeHtml(label)}</option>`).join('');
  return `<tr>
    <td><select data-p="key">${options}</select></td>
    <td><input data-p="code" value="${escapeHtml(profile.code || '')}" /></td>
    <td><input data-p="name" value="${escapeHtml(profile.name || '')}" /></td>
    <td><input data-p="width_mm" type="number" step="0.5" value="${profile.width_mm ?? ''}" /></td>
    <td><input data-p="depth_mm" type="number" step="0.5" value="${profile.depth_mm ?? ''}" /></td>
    <td><input data-p="wall_mm" type="number" step="0.1" value="${profile.wall_mm ?? 1.4}" /></td>
    <td><input data-p="kg_per_m" type="number" step="0.01" value="${profile.kg_per_m ?? ''}" /></td>
    <td><input data-p="glass_groove_mm" type="number" step="1" value="${profile.glass_groove_mm ?? 24}" /></td>
    <td><input data-p="price_per_kg" type="number" step="500" value="${profile.price_per_kg ?? ''}" /></td>
    <td><button class="icon-btn" data-p="del" title="Xóa">✕</button></td>
  </tr>`;
}

function collectSystem() {
  const system = JSON.parse(JSON.stringify(state.system || {}));
  system.code = $('#s-code').value.trim().toUpperCase();
  system.name = $('#s-name').value.trim();
  system.kind = $('#s-kind').value;
  system.joint = $('#s-joint').value;
  system.bar_length_mm = Number($('#s-bar').value) || 6500;
  system.kerf_mm = Number($('#s-kerf').value) || 0;
  system.end_trim_mm = Number($('#s-trim').value) || 0;
  system.verified = $('#s-verified').checked;
  system.source = $('#s-source').value.trim();
  system.notes = $('#s-notes').value.trim();
  system.rules = system.rules || {};
  RULE_FIELDS.forEach(([key]) => {
    const input = $(`#rule-${key}`);
    if (!input) return;
    const raw = input.value.trim();
    system.rules[key] = raw === '' ? null : Number(raw);
  });
  const profiles = {};
  $$('#profiles-body tr').forEach((row) => {
    const key = row.querySelector('[data-p="key"]').value;
    const priceRaw = row.querySelector('[data-p="price_per_kg"]').value.trim();
    profiles[key] = {
      key,
      code: row.querySelector('[data-p="code"]').value.trim(),
      name: row.querySelector('[data-p="name"]').value.trim(),
      width_mm: Number(row.querySelector('[data-p="width_mm"]').value) || 0,
      depth_mm: Number(row.querySelector('[data-p="depth_mm"]').value) || 0,
      wall_mm: Number(row.querySelector('[data-p="wall_mm"]').value) || 1.4,
      kg_per_m: Number(row.querySelector('[data-p="kg_per_m"]').value) || 0,
      glass_groove_mm: Number(row.querySelector('[data-p="glass_groove_mm"]').value) || 0,
      price_per_kg: priceRaw === '' ? null : Number(priceRaw),
    };
  });
  system.profiles = profiles;
  return system;
}

function newSystemTemplate() {
  return {
    code: 'XFM',
    name: 'Hệ mới',
    brand: 'Xingfa',
    kind: 'casement',
    joint: 'miter45',
    bar_length_mm: 6500,
    kerf_mm: 5,
    end_trim_mm: 30,
    verified: false,
    source: '',
    notes: '',
    rules: {
      gap_frame_sash_mm: 6, sash_overlap_mm: 0, glass_rebate_mm: 12, glass_clearance_mm: 4,
      min_panel_width_mm: 350, max_panel_area_m2: 2.2, track_offset_mm: 30, sash_inset_mm: null,
    },
    profiles: {
      frame: { key: 'frame', code: 'KB', name: 'Khung bao', width_mm: 55, depth_mm: 65, wall_mm: 1.4, kg_per_m: 1.5, glass_groove_mm: 24 },
      sash: { key: 'sash', code: 'C', name: 'Cửa cánh', width_mm: 60, depth_mm: 60, wall_mm: 1.4, kg_per_m: 1.35, glass_groove_mm: 24 },
      mullion: { key: 'mullion', code: 'D', name: 'Đố đứng', width_mm: 45, depth_mm: 65, wall_mm: 1.4, kg_per_m: 1.1, glass_groove_mm: 24 },
    },
  };
}

function fillPricingForms() {
  $('#pricing-json').value = JSON.stringify(state.pricing || {}, null, 2);
  $('#catalog-json').value = JSON.stringify(state.catalog || {}, null, 2);
}

function bindCatalog() {
  $('#system-list').addEventListener('click', (e) => {
    const row = e.target.closest('li[data-code]');
    if (row) openSystem(row.dataset.code);
  });

  $('#btn-add-profile').addEventListener('click', () => {
    if (!state.system) return;
    const used = Object.keys(state.system.profiles || {});
    const nextKey = PROFILE_KEYS.find(([key]) => !used.includes(key))?.[0] || 'bead';
    $('#profiles-body').insertAdjacentHTML('beforeend', profileRow(nextKey, {
      code: `${state.system.code}-${nextKey.toUpperCase()}`,
      name: PROFILE_KEYS.find(([k]) => k === nextKey)[1],
      wall_mm: 1.4,
      glass_groove_mm: 24,
    }));
  });

  $('#profiles-body').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-p="del"]');
    if (btn) btn.closest('tr').remove();
  });

  $('#btn-save-system').addEventListener('click', async () => {
    try {
      const system = collectSystem();
      await api('/api/systems', { method: 'POST', body: system });
      state.system = system;
      await loadSystems();
      renderSystemList();
      fillSystemSelect($('#p-system'), state.project.defaults.system);
      toast(`Đã lưu hệ ${system.code}`);
    } catch (err) { toast(err.message, true); }
  });

  $('#btn-new-system').addEventListener('click', () => {
    state.system = newSystemTemplate();
    renderSystem();
    renderSystemList();
    toast('Nhập thông số hệ mới rồi bấm Lưu hệ');
  });

  $('#btn-dup-system').addEventListener('click', async () => {
    if (!state.system) return;
    const suggested = `${state.system.code}X`;
    const newCode = (prompt(`Mã hệ mới (sao chép từ ${state.system.code})`, suggested) || '').trim();
    if (!newCode) return;
    try {
      await api(`/api/systems/${encodeURIComponent(state.system.code)}/duplicate`, {
        method: 'POST', body: { new_code: newCode },
      });
      await loadSystems();
      await openSystem(newCode);
      toast(`Đã nhân bản thành ${newCode}`);
    } catch (err) { toast(err.message, true); }
  });

  $('#btn-del-system').addEventListener('click', async () => {
    if (!state.system) return;
    if (!confirm(`Xóa hệ ${state.system.code}? Hành động không thể hoàn tác.`)) return;
    try {
      await api(`/api/systems/${encodeURIComponent(state.system.code)}`, { method: 'DELETE' });
      state.system = null;
      await loadSystems();
      renderSystemList();
      toast('Đã xóa hệ nhôm');
    } catch (err) { toast(err.message, true); }
  });

  $('#btn-save-pricing').addEventListener('click', async () => {
    try {
      const data = JSON.parse($('#pricing-json').value);
      const res = await api('/api/pricing', { method: 'PUT', body: data });
      state.pricing = res.pricing || data;
      fillPricingForms();
      toast('Đã lưu bảng giá');
    } catch (err) { toast(`Bảng giá JSON lỗi: ${err.message}`, true); }
  });

  $('#btn-save-catalog').addEventListener('click', async () => {
    try {
      const data = JSON.parse($('#catalog-json').value);
      await api('/api/catalog', { method: 'PUT', body: data });
      state.catalog = data;
      fillPricingForms();
      renderProject();
      toast('Đã lưu catalogue kính & phụ kiện');
    } catch (err) { toast(`Catalogue JSON lỗi: ${err.message}`, true); }
  });
}

/* ---------------- ảnh & AI ---------------- */
function applyAiItems(rawItems) {
  if (!Array.isArray(rawItems) || !rawItems.length) {
    toast('JSON không có danh sách cửa', true);
    return;
  }
  const normalized = normalizeProject({ items: rawItems }).items;
  const existing = new Set(state.project.items.map((item) => item.tag));
  normalized.forEach((item, index) => {
    let tag = item.tag || `C${state.project.items.length + index + 1}`;
    const baseTag = tag;
    let suffix = 2;
    while (existing.has(tag)) { tag = `${baseTag}-${suffix++}`; }
    item.tag = tag;
    existing.add(tag);
    const raw = rawItems[index] || {};
    if (raw.width_mm == null || raw.height_mm == null) {
      item.notes = `${item.notes} [Cần nhập kích thước]`.trim();
      item.needs_review = [...(item.needs_review || []), 'kich_thuoc'];
    }
    state.project.items.push(item);
  });
  renderItems();
  saveLocal();
  switchTab('project');
  toast(`Đã thêm ${normalized.length} cửa - kiểm tra kích thước rồi Build`);
}

function bindImage() {
  $('#file-image').addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      state.imageData = reader.result;
      $('#image-preview').innerHTML = `<img src="${state.imageData}" alt="ảnh" />`;
      $('#ai-status').textContent = `Đã nạp ảnh (${Math.round(file.size / 1024)} KB)`;
    };
    reader.readAsDataURL(file);
  });

  $('#btn-prompt').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/prompt');
      $('#prompt-text').value = await res.text();
      toast('Đã sinh prompt - copy rồi dán vào ChatGPT kèm ảnh');
    } catch (err) { toast(err.message, true); }
  });

  $('#btn-copy-prompt').addEventListener('click', async () => {
    const text = $('#prompt-text').value;
    if (!text) { toast('Bấm "Sinh prompt" trước', true); return; }
    try {
      await navigator.clipboard.writeText(text);
      toast('Đã copy prompt');
    } catch (err) {
      $('#prompt-text').select();
      document.execCommand('copy');
      toast('Đã copy prompt');
    }
  });

  $('#btn-openai').addEventListener('click', async () => {
    if (!state.status?.openai) {
      toast('Chưa cấu hình OPENAI_API_KEY - dùng cách copy prompt', true);
      return;
    }
    if (!state.imageData) { toast('Chọn ảnh trước', true); return; }
    $('#ai-status').textContent = 'Đang gọi OpenAI...';
    try {
      const res = await api('/api/extract', { method: 'POST', body: { image_base64: state.imageData } });
      const data = res.data || {};
      $('#ai-json').value = JSON.stringify(data, null, 2);
      $('#ai-status').textContent = 'Đã nhận JSON - kiểm tra rồi bấm Nhập vào dự án';
      toast('Đã trích xuất xong');
    } catch (err) {
      $('#ai-status').textContent = '';
      toast(err.message, true);
    }
  });

  $('#btn-apply-json').addEventListener('click', () => {
    try {
      const parsed = JSON.parse($('#ai-json').value);
      applyAiItems(parsed.items || parsed.data?.items || parsed);
    } catch (err) { toast(`JSON lỗi: ${err.message}`, true); }
  });
}

function bindPreview() {
  $('#preview-tabs').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    if (btn.dataset.tag) state.selectedTag = btn.dataset.tag;
    if (btn.dataset.view) state.previewTab = btn.dataset.view;
    renderPreview();
  });
}

function renderStatus() {
  const status = state.status || {};
  const freecadInfo = status.freecad || {};
  const dot = (ok, warn = false) => `<span class="dot ${ok ? 'ok' : warn ? 'warn' : 'bad'}"></span>`;
  $('#status').innerHTML = `
    <span>${dot(Boolean(freecadInfo.available))} FreeCAD</span>
    <span>${dot(Boolean(status.dxf))} DXF</span>
    <span>${dot(Boolean(status.openai), true)} OpenAI</span>
    <span>v${escapeHtml(status.version || '')}</span>`;
  if (freecadInfo.hint) $('#status').title = freecadInfo.hint;
}

async function init() {
  initTabs();
  try {
    state.status = await api('/api/status');
    state.catalog = await api('/api/catalog');
    state.pricing = await api('/api/pricing');
    state.systems = await api('/api/systems');
    renderStatus();
  } catch (err) {
    toast(`Không kết nối được API: ${err.message}`, true);
  }
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem('xfcad.project') || 'null'); } catch (err) { saved = null; }
  state.project = saved ? normalizeProject(saved) : defaultProject();
  renderProject();
  bindProject();
  bindCatalog();
  bindImage();
  bindPreview();
  fillPricingForms();
  renderSystemList();
  if (state.systems.length) {
    await openSystem(state.systems[0].code);
  } else {
    state.system = newSystemTemplate();
    renderSystem();
  }
}

document.addEventListener('DOMContentLoaded', init);
