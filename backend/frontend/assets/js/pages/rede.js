const API   = '';
const LIMIT = 4;

let currentPage = 1;
let searchQuery = '';
let debounceTimer;

const grid      = document.getElementById('rede-grid');
const pagEl     = document.getElementById('rede-pagination');
const infoEl    = document.getElementById('rede-info');
const searchInput = document.getElementById('search-input');

async function loadRede(page = 1) {
  currentPage = page;
  grid.innerHTML = `<div class="loading-state" style="grid-column:1/-1"><div class="spinner"></div> Carregando…</div>`;
  pagEl.innerHTML = '';

  const params = new URLSearchParams({ page, limit: LIMIT });
  if (searchQuery) params.set('q', searchQuery);

  try {
    const res  = await fetch(`${API}/rede?${params}`);
    const data = await res.json();
    renderGrid(data);
    renderPagination(data);
    infoEl.textContent = `${data.total} unidade${data.total !== 1 ? 's' : ''} encontrada${data.total !== 1 ? 's' : ''}`;
  } catch {
    grid.innerHTML = '<div class="error-box" style="grid-column:1/-1">Erro ao carregar a rede credenciada.</div>';
  }
}

function renderGrid(data) {
  if (!data.items?.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1">Nenhuma unidade encontrada.</div>';
    return;
  }
  grid.innerHTML = data.items.map(u => `
    <div class="unidade-card">
      <div class="unidade-card__header">
        <span class="unidade-card__cidade">${u.cidade}</span>
        ${u.tem_centro_medico ? '<span class="badge badge--cm">Centro Médico</span>' : ''}
      </div>
      <a class="unidade-card__whatsapp"
         href="https://wa.me/55${u.whatsapp.replace(/\D/g,'')}"
         target="_blank" rel="noopener">
        📱 ${u.whatsapp}
      </a>
      <div class="unidade-card__section">
        <div class="unidade-card__label">Horário WhatsApp</div>
        <div class="unidade-card__value">${u.horarios.join('<br>')}</div>
      </div>
      <div class="unidade-card__section">
        <div class="unidade-card__label">Atendente${u.atendentes.length > 1 ? 's' : ''}</div>
        ${u.atendentes.map(a => `
          <div class="atendente">
            <span class="atendente__nome">${a.nome}</span>
            <span class="atendente__email">${a.email}</span>
          </div>`).join('')}
      </div>
    </div>
  `).join('');
}

function renderPagination(data) {
  if (data.total_pages <= 1) return;

  const prev = `<button class="pagination__btn" id="pag-prev" ${data.page <= 1 ? 'disabled' : ''}>← Anterior</button>`;
  const next = `<button class="pagination__btn" id="pag-next" ${data.page >= data.total_pages ? 'disabled' : ''}>Próxima →</button>`;
  const nums = Array.from({ length: data.total_pages }, (_, i) => i + 1)
    .map(i => `<button class="pagination__btn ${i === data.page ? 'pagination__btn--active' : ''}"
                 data-page="${i}">${i}</button>`).join('');
  const info = `<span class="pagination__info">Página ${data.page} de ${data.total_pages}</span>`;

  pagEl.innerHTML = prev + nums + next + info;

  pagEl.querySelector('#pag-prev')?.addEventListener('click', () => loadRede(currentPage - 1));
  pagEl.querySelector('#pag-next')?.addEventListener('click', () => loadRede(currentPage + 1));
  pagEl.querySelectorAll('[data-page]').forEach(btn =>
    btn.addEventListener('click', () => loadRede(Number(btn.dataset.page)))
  );
}

searchInput?.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    searchQuery = searchInput.value.trim();
    loadRede(1);
  }, 300);
});

loadRede(1);
