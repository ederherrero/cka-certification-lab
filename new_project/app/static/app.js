'use strict';

// ── State ─────────────────────────────────────────────────────────
let scenarios = [];
let activeId  = null;
let ws        = null;
let busy      = false;

const SCORE_PER_SCENARIO = 10;

// ── Boot ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadScenarios();
  document.getElementById('searchInput').addEventListener('input', renderSidebar);
  initFloat();
});

// ── Data fetching ─────────────────────────────────────────────────
async function loadScenarios() {
  try {
    const res  = await fetch('/api/scenarios');
    const data = await res.json();
    scenarios  = data.scenarios;
    renderSidebar();
    updateProgress();
  } catch (e) {
    console.error('Erro ao carregar cenários:', e);
  }
}

async function loadProgress() {
  const res  = await fetch('/api/progress');
  const data = await res.json();
  scenarios.forEach(s => { s.status = data.progress[s.id] || 'idle'; });
  renderSidebar();
  updateProgress();
}

// ── Sidebar ───────────────────────────────────────────────────────
const CAT_ORDER = ['Troubleshooting','Architecture','Networking','Workloads','Storage'];
const CAT_ICONS = {
  Troubleshooting: '🔧',
  Architecture:    '🏗️',
  Networking:      '🌐',
  Workloads:       '⚙️',
  Storage:         '💾',
};

function renderSidebar() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  const list  = document.getElementById('scenarioList');
  list.innerHTML = '';

  const byCategory = {};
  scenarios.forEach(s => {
    if (query && !s.id.includes(query) && !s.title.toLowerCase().includes(query)) return;
    (byCategory[s.category] = byCategory[s.category] || []).push(s);
  });

  CAT_ORDER.forEach(cat => {
    const items = byCategory[cat];
    if (!items || !items.length) return;

    const header = document.createElement('div');
    header.className = 'category-header';
    header.textContent = `${CAT_ICONS[cat] || ''} ${cat}`;
    list.appendChild(header);

    items.forEach(s => {
      const el = document.createElement('div');
      el.className = 'scenario-item' + (s.id === activeId ? ' active' : '');
      el.onclick = () => selectScenario(s.id);

      const dot = document.createElement('div');
      dot.className = `status-dot ${s.status}`;

      const text = document.createElement('div');
      text.className = 'item-text';
      text.innerHTML = `
        <div class="item-id">${s.id}</div>
        <div class="item-title">${s.title}</div>
        <div class="item-diff">${diffLabel(s.difficulty)}</div>
      `;

      el.appendChild(dot);
      el.appendChild(text);
      list.appendChild(el);
    });
  });
}

function diffLabel(d) {
  return { iniciante: '● Iniciante', intermediario: '●● Intermediário', avancado: '●●● Avançado' }[d] || '';
}

// ── Scenario panel ────────────────────────────────────────────────
async function selectScenario(id) {
  activeId = id;
  renderSidebar();

  document.getElementById('emptyState').style.display    = 'none';
  document.getElementById('scenarioPanel').style.display = '';

  const res  = await fetch(`/api/scenarios/${id}`);
  const data = await res.json();

  document.getElementById('panelId').textContent       = data.id;
  document.getElementById('panelCategory').textContent = data.category;
  document.getElementById('panelTitle').textContent    = data.title;
  document.getElementById('panelLabRef').textContent   = data.lab_ref || '';

  const diff = document.getElementById('panelDifficulty');
  diff.textContent = diffLabel(data.difficulty);
  diff.className   = `difficulty-badge ${data.difficulty}`;

  updateStatusChip(data.status);
  clearTerminal();

  const descEl = document.getElementById('descriptionText');
  if (data.status === 'deployed' || data.status === 'verified') {
    descEl.textContent = data.description;
    descEl.classList.remove('desc-empty');
  } else {
    descEl.textContent = '';
    descEl.classList.add('desc-empty');
  }
}

function updateStatusChip(status) {
  const chip   = document.getElementById('statusChip');
  const labels = { idle: 'Não iniciado', deployed: 'Em andamento', verified: 'Concluído ✓' };
  chip.textContent = labels[status] || status;
  chip.className   = `status-chip ${status}`;
}

// ── Actions via WebSocket ─────────────────────────────────────────
function runAction(action) {
  if (!activeId || busy) return;
  busy = true;
  setButtonsDisabled(true);

  clearTerminal();
  appendLog('info', `Executando: ${action}…`);

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/${activeId}/${action}`);

  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    switch (msg.type) {
      case 'info':  appendLog('info', msg.msg); break;
      case 'ok':    appendLog('ok',  `[ok] ${msg.msg}`); break;
      case 'error': appendLog('error', `[erro] ${msg.msg}`); break;
      case 'hint':  appendLog('hint', msg.msg); break;
      case 'description': {
        const el = document.getElementById('descriptionText');
        el.textContent = msg.msg;
        el.classList.remove('desc-empty');
        break;
      }
      case 'done':
        busy = false;
        setButtonsDisabled(false);
        loadProgress().then(() => {
          const sc = scenarios.find(s => s.id === activeId);
          if (sc) updateStatusChip(sc.status);
        });
        updateProgress();
        break;
    }
  };

  ws.onerror = () => { appendLog('error', 'Erro na conexão WebSocket.'); busy = false; setButtonsDisabled(false); };
  ws.onclose = () => { busy = false; setButtonsDisabled(false); };
}

// ── Output helpers ────────────────────────────────────────────────
function appendLog(type, text) {
  const body = document.getElementById('terminalBody');
  const line = document.createElement('div');
  line.className = `log-${type}`;
  if (type === 'hint') {
    line.innerHTML = '<strong>💡 Dica:</strong><br>' + escHtml(text);
  } else {
    line.textContent = text;
  }
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

function clearTerminal() {
  document.getElementById('terminalBody').innerHTML =
    '<span class="terminal-placeholder">Aguardando ação…</span>';
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Progress bar ──────────────────────────────────────────────────
function updateProgress() {
  const total    = scenarios.length;
  const verified = scenarios.filter(s => s.status === 'verified').length;
  const pct      = total ? (verified / total) * 100 : 0;
  document.getElementById('progressFill').style.width  = pct + '%';
  document.getElementById('progressLabel').textContent = `${verified} / ${total}`;
  document.getElementById('scoreBadge').textContent    = `${verified * SCORE_PER_SCENARIO} pts`;
}

function setButtonsDisabled(disabled) {
  ['btnDeploy','btnVerify','btnHint','btnReset'].forEach(id => {
    document.getElementById(id).disabled = disabled;
  });
}

// ── Janela flutuante ──────────────────────────────────────────────
let floatMin = false;
let floatMax = false;
let savedPos = {};

function initFloat() {
  const win   = document.getElementById('termFloat');
  const hdr   = document.getElementById('termDragHandle');
  const rsz   = document.getElementById('termResizeHandle');
  const frame = document.getElementById('termFrame');

  let dragging = false, resizing = false;
  let ox = 0, oy = 0, rsx = 0, rsy = 0, rsw = 0, rsh = 0;

  function snapToPixels() {
    // Substitui transform CSS por coordenadas absolutas
    if (win.style.transform !== 'none') {
      const r = win.getBoundingClientRect();
      win.style.left      = r.left + 'px';
      win.style.top       = r.top  + 'px';
      win.style.transform = 'none';
    }
  }

  // ── Arrastar ──
  hdr.addEventListener('mousedown', e => {
    if (floatMax || e.target.classList.contains('dot') || e.target.classList.contains('float-btn')) return;
    dragging = true;
    snapToPixels();
    ox = e.clientX - win.offsetLeft;
    oy = e.clientY - win.offsetTop;
    frame.style.pointerEvents = 'none'; // evita que o iframe consuma o mouse
    e.preventDefault();
  });

  // ── Redimensionar ──
  rsz.addEventListener('mousedown', e => {
    resizing = true;
    snapToPixels();
    rsx = e.clientX; rsy = e.clientY;
    rsw = win.offsetWidth; rsh = win.offsetHeight;
    frame.style.pointerEvents = 'none';
    e.preventDefault(); e.stopPropagation();
  });

  document.addEventListener('mousemove', e => {
    if (dragging) {
      win.style.left = Math.max(0, Math.min(window.innerWidth  - 100, e.clientX - ox)) + 'px';
      win.style.top  = Math.max(0, Math.min(window.innerHeight - 36,  e.clientY - oy)) + 'px';
    }
    if (resizing) {
      win.style.width  = Math.max(320, rsw + e.clientX - rsx) + 'px';
      win.style.height = Math.max(160, rsh + e.clientY - rsy) + 'px';
    }
  });

  document.addEventListener('mouseup', () => {
    if (dragging || resizing) frame.style.pointerEvents = '';
    dragging = false;
    resizing = false;
  });

  // Duplo clique na barra: toggle minimizar
  hdr.addEventListener('dblclick', () => floatMinimize());
}

function floatMinimize() {
  floatMin = !floatMin;
  document.getElementById('termFloat').classList.toggle('float-minimized', floatMin);
}

function floatMaximize() {
  const win     = document.getElementById('termFloat');
  const sidebar = document.querySelector('.sidebar');
  const headerH = document.querySelector('header').offsetHeight;

  if (!floatMax) {
    const r = win.getBoundingClientRect();
    savedPos = {
      left: win.style.left, top: win.style.top,
      width: win.style.width, height: win.style.height,
      transform: win.style.transform,
    };
    const sw = sidebar.offsetWidth;
    win.style.transform = 'none';
    win.style.left      = sw + 'px';
    win.style.top       = headerH + 'px';
    win.style.width     = (window.innerWidth  - sw) + 'px';
    win.style.height    = (window.innerHeight - headerH) + 'px';
    floatMax = true;
    win.classList.add('float-maximized');
  } else {
    floatRestore();
  }
}

function floatRestore() {
  const win = document.getElementById('termFloat');
  if (floatMax && savedPos.left) {
    Object.assign(win.style, savedPos);
  } else {
    // Volta ao padrão CSS
    win.style.cssText = '';
  }
  floatMax = false;
  floatMin = false;
  win.classList.remove('float-maximized', 'float-minimized');
}

function reloadTerm() {
  const f = document.getElementById('termFrame');
  f.src = f.src;
}
