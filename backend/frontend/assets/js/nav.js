/**
 * nav.js — injeta a navbar e o modal do chat em todas as páginas
 * e marca o item ativo pela URL atual.
 */
(function () {
  const NAV_ITEMS = [
    { label: 'Rol ANS',   href: '/pages/rol.html',     key: 'rol'      },
    { label: 'Planos',    href: '/pages/planos.html',  key: 'planos'   },
    { label: 'Carência',  href: '/pages/carencia.html', key: 'carencia' },
    { label: 'Rede',      href: '/pages/rede.html',    key: 'rede'     },
    { label: 'CME',       href: '/pages/cme.html',     key: 'cme'      },
    { label: 'Contato',   href: '/pages/contato.html', key: 'contato'  },
  ];

  const current = location.pathname.split('/').pop() || 'index.html';

  const books = NAV_ITEMS.map(item => {
    const itemFile = item.href.split('/').pop();
    const isActive = current === itemFile || (current === '' && itemFile === 'index.html');
    return `
      <a href="${item.href}" class="book${isActive ? ' active' : ''}">
        <span class="book-body"><span class="book-title">${item.label}</span></span>
      </a>`;
  }).join('');

  document.body.insertAdjacentHTML('afterbegin', `
    <header class="navbar">
      <div class="navbar-inner">
        <nav class="shelf" aria-label="Menu principal">${books}</nav>
      </div>
    </header>`);

  // Modal do chat
  document.body.insertAdjacentHTML('beforeend', `
    <div class="chat-modal-overlay" id="chatModalOverlay"></div>
    <div class="chat-modal" id="chatModal">
      <div class="chat-modal-header">
        <div class="chat-modal-title">
          <img src="https://th.bing.com/th/id/ODF.aE0r0MnfIatFjr5PFky3Wg?w=24&h=24&qlt=90&pcl=fffffa&o=6&pid=1.2" alt="Oeste Saúde" />
          <span>Assistente Virtual</span>
        </div>
        <button class="chat-modal-close" id="chatModalClose" aria-label="Fechar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="chat-modal-body">
        <div class="chat-box" id="chatBox"></div>
        <div class="chat-context-bar">
          <button class="chat-context-btn" id="contextBtn" aria-label="Passar contexto da página">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            <span>Passar contexto da página</span>
          </button>
        </div>
        <form class="chat-form" id="chatForm">
          <input type="text" id="chatInput" class="chat-input" placeholder="Digite sua mensagem..." autocomplete="off" required />
          <button type="submit" class="chat-send" id="chatSend" aria-label="Enviar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>
      </div>
    </div>
    <button class="fab" id="chatFab" aria-label="Abrir assistente virtual">
      <img src="https://th.bing.com/th/id/ODF.aE0r0MnfIatFjr5PFky3Wg?w=32&h=32&qlt=90&pcl=fffffa&o=6&pid=1.2"
           alt="Oeste Saúde" />
    </button>`);

  // Toggle do modal
  const fab = document.getElementById('chatFab');
  const modal = document.getElementById('chatModal');
  const overlay = document.getElementById('chatModalOverlay');
  const closeBtn = document.getElementById('chatModalClose');

  function toggleModal() {
    const isOpen = modal.classList.contains('open');
    if (isOpen) {
      modal.classList.remove('open');
      overlay.classList.remove('open');
    } else {
      modal.classList.add('open');
      overlay.classList.add('open');
      // Verificar status do navegador quando abrir
      if (window.chatModalCheckStatus) {
        window.chatModalCheckStatus();
      }
      // Focar no input se o chat estiver pronto
      setTimeout(() => {
        const chatInput = document.getElementById('chatInput');
        if (chatInput && !chatInput.disabled) {
          chatInput.focus();
        }
      }, 300);
    }
  }

  function closeModal() {
    modal.classList.remove('open');
    overlay.classList.remove('open');
  }

  fab.addEventListener('click', toggleModal);
  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', closeModal);

  // Botão de contexto dentro do modal
  const contextBtn = document.getElementById('contextBtn');
  contextBtn.addEventListener('click', async function() {
    // Extrair conteúdo da página
    const pageContent = extractPageContent();
    
    // Verificar status e enviar contexto
    if (window.chatModalCheckStatus) {
      window.chatModalCheckStatus();
    }
    
    // Enviar contexto via função global do chat.js
    if (window.sendContextToGemini) {
      window.sendContextToGemini(pageContent);
    }
  });

  function extractPageContent() {
    // Extrair texto relevante da página (excluindo o modal)
    const mainContent = document.querySelector('.page-main');
    if (mainContent) {
      return mainContent.innerText.trim().substring(0, 4000); // Limitar a 4000 chars
    }
    // Fallback: extrair do body excluindo o modal
    const modal = document.getElementById('chatModal');
    const overlay = document.getElementById('chatModalOverlay');
    const contextBtn = document.getElementById('contextFab');
    const fab = document.getElementById('chatFab');
    
    const bodyClone = document.body.cloneNode(true);
    const elementsToRemove = bodyClone.querySelectorAll('#chatModal, #chatModalOverlay, #contextFab, #chatFab, .navbar');
    elementsToRemove.forEach(el => el.remove());
    
    return bodyClone.innerText.trim().substring(0, 4000);
  }

  // Carregar estilos e scripts do chat dinamicamente
  const chatCss = document.createElement('link');
  chatCss.rel = 'stylesheet';
  chatCss.href = '/assets/css/chat.css';
  document.head.appendChild(chatCss);

  const markedScript = document.createElement('script');
  markedScript.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
  markedScript.onload = function() {
    const chatScript = document.createElement('script');
    chatScript.src = '/assets/js/chat.js';
    document.body.appendChild(chatScript);
  };
  document.body.appendChild(markedScript);
})();
