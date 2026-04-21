const API = '';

const viewSearch      = document.getElementById('view-search');
const viewDetail      = document.getElementById('view-detail');
const detailContainer = document.getElementById('detail-container');
const searchInput     = document.getElementById('search-input');
const searchBtn       = document.getElementById('search-btn');
const statusBar       = document.getElementById('status-bar');
const resultsList     = document.getElementById('results-list');

let debounceTimer;

// ─── Views ────────────────────────────────────────────────────
function showSearch() {
  viewSearch.classList.remove('hidden');
  viewDetail.classList.add('hidden');
  window.scrollTo({ top: 0 });
  searchInput.focus();
}
function showDetail() {
  viewSearch.classList.add('hidden');
  viewDetail.classList.remove('hidden');
  window.scrollTo({ top: 0 });
}

// ─── Status ───────────────────────────────────────────────────
function setStatus(msg, type = 'info') {
  statusBar.textContent = msg;
  statusBar.className = `status-bar status-bar--${type}`;
}
function clearStatus() { statusBar.className = 'status-bar hidden'; }

// ─── Segmentação ──────────────────────────────────────────────
const SEG = {
  amb: { label: 'Ambulatorial',              color: '#00923f' },
  hco: { label: 'Hospitalar c/ Obstetrícia', color: '#0072b8' },
  hso: { label: 'Hospitalar s/ Obstetrícia', color: '#1565c0' },
  od:  { label: 'Odontológico',              color: '#6a1b9a' },
  pac: { label: 'Prog. Atenção Continuada',  color: '#00838f' },
};

function segBadges(seg) {
  if (!seg) return '';
  return Object.entries(SEG)
    .filter(([k]) => seg[k])
    .map(([k, s]) => `<span class="badge badge--seg" title="${s.label}">${k.toUpperCase()}</span>`)
    .join('');
}

function segPills(seg) {
  if (!seg) return '<span class="text-muted">Não informado</span>';
  const pills = Object.entries(SEG)
    .filter(([k]) => seg[k])
    .map(([k, s]) => `
      <div class="seg-pill" style="--pc:${s.color}">
        <span class="seg-pill__key">${k.toUpperCase()}</span>
        <span class="seg-pill__label">${s.label}</span>
      </div>`).join('');
  return pills || '<span class="text-muted">Não informado</span>';
}

// ─── Card de resultado ────────────────────────────────────────
function createCard(item) {
  const procs = item.procedimentos_rol ?? [];
  const cob   = item.cobertura_obrigatoria
    ? `<span class="badge badge--cob">Cobertura obrigatória</span>`
    : `<span class="badge badge--nao">Sem cobertura ANS</span>`;

  // Verifica se há algum DUT associado aos procedimentos
  const hasDut = procs.some(p => p.dut && p.dut !== '---');
  const dutBadge = hasDut ? `<span class="badge badge--dut" title="Requer Diretriz de Utilização (DUT)">DUT</span>` : '';

  // Mostra todos os procedimentos
  const procsHtml = procs.length > 0 
    ? procs.map(p => `<div class="result-card__proc">${p.nome}</div>`).join('')
    : `<div class="result-card__proc">${item.descricao_tuss ?? '—'}</div>`;

  const el = document.createElement('div');
  el.className = 'result-card';
  el.innerHTML = `
    <div class="result-card__top">
      <span class="result-card__code">${item.codigo_tuss ?? '—'}</span>${cob}${dutBadge}
    </div>
    <div class="result-card__name">${item.descricao_tuss ?? '—'}</div>
    ${item.descricao_tuss ? `<div class="result-card__procs">${procsHtml}</div>` : ''}
    <div class="result-card__badges">${segBadges(item.segmentacao)}</div>
    <span class="result-card__arrow">›</span>
  `;
  const procNome = procs[0]?.nome || '';
  el.addEventListener('click', () => loadDetail(item.codigo_tuss, procNome));
  return el;
}

// ─── Paginação local ──────────────────────────────────────────
const PAGE_SIZE = 10;
let allItems    = [];
let currentPage = 1;

function totalPages() { return Math.ceil(allItems.length / PAGE_SIZE); }

function renderPage(page) {
  currentPage = page;
  const start = (page - 1) * PAGE_SIZE;
  const slice = allItems.slice(start, start + PAGE_SIZE);

  resultsList.innerHTML = '';
  slice.forEach(item => resultsList.appendChild(createCard(item)));
  resultsList.classList.remove('hidden');

  renderPagination();
}

function renderPagination() {
  const total = totalPages();
  let pag = document.getElementById('rol-pagination');
  if (!pag) {
    pag = document.createElement('div');
    pag.id = 'rol-pagination';
    pag.className = 'pagination';
    resultsList.after(pag);
  }

  if (total <= 1) { pag.innerHTML = ''; return; }

  pag.innerHTML = `
    <button class="pagination__btn" id="pag-prev" ${currentPage <= 1 ? 'disabled' : ''}>‹</button>
    <span class="pagination__info">${currentPage} de ${total}</span>
    <button class="pagination__btn" id="pag-next" ${currentPage >= total ? 'disabled' : ''}>›</button>
  `;

  pag.querySelector('#pag-prev').addEventListener('click', () => {
    if (currentPage > 1) { renderPage(currentPage - 1); window.scrollTo({ top: 0 }); }
  });
  pag.querySelector('#pag-next').addEventListener('click', () => {
    if (currentPage < total) { renderPage(currentPage + 1); window.scrollTo({ top: 0 }); }
  });
}

// ─── Busca ────────────────────────────────────────────────────
async function search(q) {
  q = q?.trim();
  if (!q || q.length < 2) return;

  resultsList.innerHTML = '';
  resultsList.classList.add('hidden');
  const pag = document.getElementById('rol-pagination');
  if (pag) pag.innerHTML = '';
  setStatus('Buscando…');
  searchBtn.disabled = true;

  console.log('[rol] buscando:', q);

  try {
    const res  = await fetch(`${API}/procedimentos?q=${encodeURIComponent(q)}&limit=100`);
    console.log('[rol] status HTTP:', res.status);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log('[rol] total:', data.total, '| items:', data.items?.length);

    clearStatus();
    searchBtn.disabled = false;

    if (!data.items?.length) { setStatus('Nenhum procedimento encontrado.', 'warn'); return; }

    allItems = data.items;
    setStatus(`${data.total} resultado${data.total !== 1 ? 's' : ''} encontrado${data.total !== 1 ? 's' : ''}.`, 'ok');
    renderPage(1);
  } catch (err) {
    console.error('[rol] erro:', err);
    searchBtn.disabled = false;
    setStatus('Erro ao conectar com a API.', 'error');
  }
}

// ─── Carregar dados iniciais ─────────────────────────────────────
async function loadInitial() {
  resultsList.innerHTML = '';
  resultsList.classList.add('hidden');
  const pag = document.getElementById('rol-pagination');
  if (pag) pag.innerHTML = '';
  setStatus('Carregando…');

  try {
    const res = await fetch(`${API}/procedimentos?limit=100`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    clearStatus();

    if (!data.items?.length) { setStatus('Nenhum procedimento encontrado.', 'warn'); return; }

    allItems = data.items;
    renderPage(1);
  } catch (err) {
    console.error('[rol] erro:', err);
    setStatus('Erro ao conectar com a API.', 'error');
  }
}

// Carregar dados iniciais ao abrir a página
loadInitial();

searchBtn.addEventListener('click', () => search(searchInput.value));
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') search(searchInput.value); });
searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  if (searchInput.value.trim().length >= 3)
    debounceTimer = setTimeout(() => search(searchInput.value), 500);
});

// ─── Detalhe ──────────────────────────────────────────────────
async function loadDetail(codigo, procNome = null) {
  showDetail();
  detailContainer.innerHTML = `<div class="wrap"><div class="loading-state"><div class="spinner"></div> Carregando…</div></div>`;

  try {
    const res  = await fetch(`${API}/procedimentos/${encodeURIComponent(codigo)}`);
    if (!res.ok) throw new Error();
    const data = await res.json();

    // Se um nome de procedimento foi passado, filtra para mostrar apenas ele
    if (procNome && data.procedimentos_rol) {
      data.procedimentos_rol = data.procedimentos_rol.filter(p => p.nome === procNome);
    }

    const dutNums = [...new Set(
      (data.procedimentos_rol ?? [])
        .map(p => p.dut)
        .filter(d => d && d !== '---' && /^\d+(\.\d+)?$/.test(d.trim()))
    )];
    const dutMap  = {};
    await Promise.all(dutNums.map(async num => {
      try {
        const r = await fetch(`${API}/dut/${encodeURIComponent(num)}`);
        if (r.ok) dutMap[num] = await r.json();
      } catch {}
    }));

    renderDetail(data, dutMap);
  } catch {
    detailContainer.innerHTML = `
      <div class="wrap">
        <button class="btn-back" id="btn-back">← Voltar</button>
        <div class="error-box">Erro ao carregar o procedimento.</div>
      </div>`;
    document.getElementById('btn-back').addEventListener('click', showSearch);
  }
}

function formatCriterios(texto) {
  if (!texto) return '<p class="text-muted">Critérios não disponíveis.</p>';

  // Normaliza quebras de linha
  let normalized = texto
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .trim();

  // Divide em linhas
  let lines = normalized.split('\n').map(l => l.trim()).filter(Boolean);

  let html = '';
  let inNumberedList = false;
  let inBulletList = false;
  let inSubList = false;

  for (let line of lines) {
    // Detecta início de lista numerada principal (1., 2., 3.)
    if (/^\d+\.\s/.test(line)) {
      if (inBulletList) { html += '</ul>'; inBulletList = false; }
      if (inSubList) { html += '</ul>'; inSubList = false; }
      if (!inNumberedList) { html += '<ol class="crit-list">'; inNumberedList = true; }
      html += `<li>${line.replace(/^\d+\.\s/, '')}</li>`;
    }
    // Detecta sub-item (a., b., c.)
    else if (/^[a-z]\.\s/.test(line)) {
      if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
      if (!inSubList) { html += '<ul class="crit-sublist">'; inSubList = true; }
      html += `<li>${line.replace(/^[a-z]\.\s/, '')}</li>`;
    }
    // Detecta bullet (•)
    else if (/^•\s/.test(line)) {
      if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
      if (inSubList) { html += '</ul>'; inSubList = false; }
      if (!inBulletList) { html += '<ul class="crit-bullet">'; inBulletList = true; }
      html += `<li>${line.replace(/^•\s/, '')}</li>`;
    }
    // Texto normal (títulos, observações, etc)
    else {
      if (inNumberedList) { html += '</ol>'; inNumberedList = false; }
      if (inBulletList) { html += '</ul>'; inBulletList = false; }
      if (inSubList) { html += '</ul>'; inSubList = false; }
      
      // Detecta se é título (Observações:, Para fins de utilização, etc)
      if (/^(Observações|Para fins de utilização|Nota|Importante):/i.test(line)) {
        html += `<p class="crit-title">${line}</p>`;
      } else {
        html += `<p class="crit-text">${line}</p>`;
      }
    }
  }

  // Fecha listas abertas
  if (inNumberedList) html += '</ol>';
  if (inBulletList) html += '</ul>';
  if (inSubList) html += '</ul>';

  return html;
}

function renderDetail(data, dutMap) {
  const seg    = data.segmentacao ?? {};
  const procs  = data.procedimentos_rol ?? [];
  const coberto = data.cobertura_obrigatoria;

  const crumbs = [data.capitulo, data.grupo, data.subgrupo]
    .filter(Boolean).filter((v, i, a) => a.indexOf(v) === i);
  const breadcrumb = crumbs.length
    ? `<div class="breadcrumb">${crumbs.map(c =>
        `<span class="breadcrumb__item">${c}</span>`).join('<span class="breadcrumb__sep">›</span>')}</div>`
    : '';

  // Seção de dados do código TUSS (skeleton - todos os campos)
  const tussFields = [
    { label: 'Código TUSS', value: data.codigo_tuss || '—' },
    { label: 'Descrição TUSS', value: data.descricao_tuss || '—' },
    { label: 'Correlação', value: data.correlacao || '—' },
    { label: 'Capítulo', value: data.capitulo || '—' },
    { label: 'Grupo', value: data.grupo || '—' },
    { label: 'Subgrupo', value: data.subgrupo || '—' },
  ];

  const tussHtml = tussFields.map(f => `
    <div class="skeleton-field">
      <div class="skeleton-field__label">${f.label}</div>
      <div class="skeleton-field__value">${f.value}</div>
    </div>
  `).join('');

  // Seção de segmentação (skeleton - todos os campos)
  const segFields = [
    { label: 'Odontológico (OD)', value: seg.od ? 'Sim' : 'Não' },
    { label: 'Ambulatorial (AMB)', value: seg.amb ? 'Sim' : 'Não' },
    { label: 'Hospitalar c/ Obstetrícia (HCO)', value: seg.hco ? 'Sim' : 'Não' },
    { label: 'Hospitalar s/ Obstetrícia (HSO)', value: seg.hso ? 'Sim' : 'Não' },
    { label: 'Programa Atenção Continuada (PAC)', value: seg.pac ? 'Sim' : 'Não' },
  ];

  const segHtml = segFields.map(f => `
    <div class="skeleton-field">
      <div class="skeleton-field__label">${f.label}</div>
      <div class="skeleton-field__value ${f.value === 'Sim' ? 'value-yes' : 'value-no'}">${f.value}</div>
    </div>
  `).join('');

  // Seção de procedimentos correlacionados (skeleton - todos os campos)
  const procsHtml = procs.length ? procs.map((p, idx) => {
    const dut = p.dut ? dutMap[p.dut] : null;
    
    // Campos do procedimento
    const procFields = [
      { label: 'Nome do procedimento', value: p.nome || '—' },
      { label: 'DUT', value: p.dut || '—' },
      { label: 'RN', value: p.rn || '—' },
    ];

    const procFieldsHtml = procFields.map(f => `
      <div class="skeleton-field">
        <div class="skeleton-field__label">${f.label}</div>
        <div class="skeleton-field__value">${f.value}</div>
      </div>
    `).join('');

    // Campos da DUT (skeleton - todos os campos)
    let dutFieldsHtml = '';
    if (dut) {
      const dutFields = [
        { label: 'Número DUT', value: dut.numero || '—' },
        { label: 'Nome DUT', value: dut.nome || '—' },
        { label: 'RN DUT', value: dut.rn || '—' },
        { label: 'Vigência DUT', value: dut.vigencia || '—' },
        { label: 'Tem subitens', value: dut.tem_subitens ? 'Sim' : 'Não' },
      ];

      dutFieldsHtml = dutFields.map(f => `
        <div class="skeleton-field">
          <div class="skeleton-field__label">${f.label}</div>
          <div class="skeleton-field__value">${f.value}</div>
        </div>
      `).join('');

      dutFieldsHtml += `
        <div style="margin-top: 16px;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted); margin-bottom: 8px;">Critérios</div>
          <div class="criterios-text">${formatCriterios(dut.criterios ?? '')}</div>
        </div>
      `;
    } else if (p.dut) {
      dutFieldsHtml = `
        <div class="skeleton-field skeleton-field--full">
          <div class="skeleton-field__label">Status DUT</div>
          <div class="skeleton-field__value value-error">DUT ${p.dut} não disponível no banco</div>
        </div>
      `;
    } else {
      dutFieldsHtml = `
        <div class="skeleton-field skeleton-field--full">
          <div class="skeleton-field__label">Status DUT</div>
          <div class="skeleton-field__value">Não aplicável</div>
        </div>
      `;
    }

    const procTitle = procs.length === 1 ? p.nome : `Procedimento ${idx + 1}`;
    return `
      <div class="proc-block">
        <div class="proc-block__header">
          <span class="proc-block__title">${procTitle}</span>
        </div>
        <div class="skeleton-grid">${procFieldsHtml}</div>
        ${dutFieldsHtml ? `<div class="skeleton-section"><div class="skeleton-section__title">Diretriz de Utilização (DUT)</div><div class="skeleton-grid">${dutFieldsHtml}</div></div>` : ''}
      </div>`;
  }).join('') : '<p class="text-muted">Nenhum procedimento correlacionado no Rol ANS.</p>';

  detailContainer.innerHTML = `
    <div class="wrap">
      <button class="btn-back" id="btn-back">← Voltar aos resultados</button>

      <div class="detail-hero ${coberto ? 'detail-hero--cob' : 'detail-hero--nao'}">
        <div class="detail-hero__left">
          <span class="detail-hero__code">TUSS ${data.codigo_tuss ?? '—'}</span>
          <h2 class="detail-hero__title">${data.descricao_tuss ?? '—'}</h2>
          ${breadcrumb}
        </div>
        <div class="cob-badge ${coberto ? 'cob-badge--sim' : 'cob-badge--nao'}">
          ${coberto ? 'SIM' : 'NÃO'}
          <span>${coberto ? 'Cobertura<br>obrigatória' : 'Sem cobertura<br>obrigatória'}</span>
        </div>
      </div>

      <div class="detail-section">
        <h3 class="detail-section__title">Dados do Código TUSS</h3>
        <div class="skeleton-grid">${tussHtml}</div>
      </div>

      <div class="detail-section">
        <h3 class="detail-section__title">Segmentação do Plano</h3>
        <div class="skeleton-grid">${segHtml}</div>
      </div>

      <div class="detail-section">
        <h3 class="detail-section__title">
          Procedimentos Correlacionados no Rol ANS
          ${procs.length ? `<span class="count-badge">${procs.length}</span>` : ''}
        </h3>
        <div class="proc-blocks">${procsHtml}</div>
      </div>
    </div>
  `;

  document.getElementById('btn-back').addEventListener('click', showSearch);
}
