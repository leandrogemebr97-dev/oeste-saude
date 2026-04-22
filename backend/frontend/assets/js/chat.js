(function () {
  const chatBox = document.getElementById('chatBox');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');

  const API_URL = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
    ? 'http://localhost:8001'
    : window.location.origin;

  const STORAGE_KEY = 'oeste_chat_messages';
  const STORAGE_STATE = 'oeste_chat_state';
  const WARNING_SHOWN_KEY = 'oeste_chat_warning_shown';
  const SERVER_ID_KEY = 'oeste_chat_server_id';

  let isReady = false;
  let currentServerId = null;
  let statusInterval = null;
  let messages = [];

  function appendBubble(text, sender, save = true) {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-message--' + sender;
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble--' + sender;
    
    if (sender === 'bot' && typeof marked !== 'undefined') {
      // Renderizar markdown para respostas do bot
      bubble.innerHTML = marked.parse(text);
    } else {
      bubble.textContent = text;
    }
    
    msg.appendChild(bubble);
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    // Salvar no array e localStorage
    if (save) {
      messages.push({ text, sender, timestamp: Date.now() });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
    
    return msg;
  }

  function loadMessages() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        messages = JSON.parse(stored);
        messages.forEach(m => {
          const msg = document.createElement('div');
          msg.className = 'chat-message chat-message--' + m.sender;
          const bubble = document.createElement('div');
          bubble.className = 'chat-bubble chat-bubble--' + m.sender;
          
          if (m.sender === 'bot' && typeof marked !== 'undefined') {
            bubble.innerHTML = marked.parse(m.text);
          } else {
            bubble.textContent = m.text;
          }
          
          msg.appendChild(bubble);
          chatBox.appendChild(msg);
        });
        chatBox.scrollTop = chatBox.scrollHeight;
      } catch (e) {
        console.error('Erro ao carregar mensagens:', e);
        messages = [];
      }
    }
  }

  function clearChat() {
    messages = [];
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_STATE);
    localStorage.removeItem(WARNING_SHOWN_KEY);
    chatBox.innerHTML = '';
    showStartButton();
  }

  function showStartButton() {
    // Remover qualquer mensagem de início existente
    const existing = document.getElementById('initMessage');
    if (existing) {
      existing.remove();
    }
    
    const initMsg = document.createElement('div');
    initMsg.id = 'initMessage';
    initMsg.className = 'chat-message chat-message--bot';
    initMsg.innerHTML = `
      <div class="chat-bubble chat-bubble--info">
        <button id="startBtn" class="start-button">Iniciar Assistente</button>
        <button id="clearBtn" class="clear-button" style="margin-left: 10px; background: #dc2626;">Limpar</button>
      </div>
    `;
    chatBox.appendChild(initMsg);
    
    document.getElementById('startBtn').addEventListener('click', startAssistant);
    document.getElementById('clearBtn').addEventListener('click', clearChat);
  }

  function appendLoading() {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-message--bot';
    msg.id = 'chatLoading';
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble--loading';
    bubble.textContent = 'Digitando...';
    msg.appendChild(bubble);
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
  }

  function removeLoading() {
    const el = document.getElementById('chatLoading');
    if (el) el.remove();
  }

  function appendError(text) {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-message--bot';
    const bubble = document.createElement('div');
    bubble.className = 'chat-error';
    bubble.textContent = text;
    msg.appendChild(bubble);
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function appendInfo(text) {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-message--bot';
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble--info';
    bubble.innerHTML = text;
    msg.appendChild(bubble);
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function setReady(ready) {
    isReady = ready;
    chatInput.disabled = !ready;
    chatSend.disabled = !ready;
    // Também controlar botão de contexto
    const contextBtn = document.getElementById('contextBtn');
    if (contextBtn) contextBtn.disabled = !ready;
    if (ready) {
      chatInput.placeholder = 'Digite sua mensagem...';
      chatInput.focus();
    } else {
      chatInput.placeholder = 'Aguardando navegador...';
    }
  }

  async function checkStatus() {
    try {
      const res = await fetch(API_URL + '/chat/status');
      const data = await res.json();
      if (data.ready && !isReady) {
        setReady(true);
        const initMsg = document.getElementById('initMessage');
        if (initMsg) initMsg.remove();
        if (statusInterval) {
          clearInterval(statusInterval);
          statusInterval = null;
        }
        // Salvar estado e server_id
        localStorage.setItem(STORAGE_STATE, JSON.stringify({ ready: true, timestamp: Date.now() }));
        if (data.server_id) {
          localStorage.setItem(SERVER_ID_KEY, data.server_id);
          currentServerId = data.server_id;
        }
      }
    } catch (e) {
      console.error('Erro ao verificar status:', e);
    }
  }

  function handleBrowserClosed() {
    // Sempre marcar como não pronto
    setReady(false);
    localStorage.removeItem(STORAGE_STATE);
    
    // Sempre mostrar o botão iniciar (remove e recria se necessário)
    showStartButton();
    
    // Adicionar mensagem de aviso
    const existingWarning = document.querySelector('.browser-closed-warning');
    if (!existingWarning) {
      const msg = document.createElement('div');
      msg.className = 'chat-message chat-message--bot browser-closed-warning';
      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble chat-bubble--info';
      bubble.innerHTML = '<strong>Navegador foi fechado.</strong><br>Clique em "Iniciar Assistente" para continuar.';
      msg.appendChild(bubble);
      chatBox.appendChild(msg);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }
  
  async function checkBrowserStatus() {
    // Verificar se o navegador ainda está rodando
    try {
      const res = await fetch(API_URL + '/chat/status');
      const data = await res.json();
      
      // Verificar se servidor reiniciou (server_id mudou)
      if (data.server_id && currentServerId && data.server_id !== currentServerId) {
        // Servidor reiniciou - limpar tudo
        localStorage.removeItem(STORAGE_STATE);
        localStorage.removeItem(WARNING_SHOWN_KEY);
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(SERVER_ID_KEY);
        messages = [];
        chatBox.innerHTML = '';
        currentServerId = data.server_id;
        setReady(false);
        showStartButton();
        return;
      }
      
      // Atualizar server_id atual
      if (data.server_id) {
        currentServerId = data.server_id;
      }
      
      const storedState = localStorage.getItem(STORAGE_STATE);
      const wasReady = storedState ? JSON.parse(storedState).ready : false;
      
      if (data.ready) {
        setReady(true);
        // Limpar flag de aviso quando navegador estiver pronto
        localStorage.removeItem(WARNING_SHOWN_KEY);
        // Remover botão iniciar se existir
        const initMsg = document.getElementById('initMessage');
        if (initMsg) initMsg.remove();
        // Atualizar estado no localStorage
        localStorage.setItem(STORAGE_STATE, JSON.stringify({ ready: true, timestamp: Date.now() }));
        localStorage.setItem(SERVER_ID_KEY, data.server_id);
        
        // Habilitar botão de contexto
        const contextBtn = document.getElementById('contextBtn');
        if (contextBtn) contextBtn.disabled = false;
      } else if (wasReady || isReady) {
        // Navegador foi fechado - detecta tanto pelo localStorage quanto pelo estado local
        handleBrowserClosed();
      }
    } catch (e) {
      console.error('Erro ao verificar status:', e);
    }
  }

  async function startAssistant() {
    const initMsg = document.getElementById('initMessage');
    if (initMsg) initMsg.remove();

    // Limpar flags para permitir aviso futuro se navegador for fechado
    localStorage.removeItem(WARNING_SHOWN_KEY);
    
    appendInfo(`
      <strong>Iniciando navegador...</strong>
    `, false);

    setReady(false);

    // Iniciar navegador via backend
    try {
      const res = await fetch(API_URL + '/chat/start', {
        method: 'POST',
      });
      const data = await res.json();
      
      if (data.success) {
        appendInfo(`
          <strong>${data.message}</strong><br>
          Aguarde enquanto restauramos a conversa...
        `, false);
        
        // Aguardar navegador ficar pronto e enviar histórico
        await waitForBrowserAndSendHistory();
      } else {
        appendInfo(`
          <strong>Erro ao iniciar navegador:</strong><br>
          ${data.message}
        `, false);
      }
    } catch (e) {
      appendInfo(`
        <strong>Erro ao iniciar navegador:</strong><br>
        ${e.message}
      `, false);
    }
  }
  
  async function waitForBrowserAndSendHistory() {
    // Aguardar até 30 segundos pelo navegador ficar pronto
    let attempts = 0;
    const maxAttempts = 30;
    
    while (attempts < maxAttempts) {
      try {
        const res = await fetch(API_URL + '/chat/status');
        const data = await res.json();
        
        if (data.ready) {
          setReady(true);
          browserClosedWarningShown = false;
          
          // Enviar histórico das mensagens para o Gemini
          await sendConversationHistory();
          
          // Remover mensagens de warning
          const warnings = document.querySelectorAll('.browser-closed-warning');
          warnings.forEach(w => w.remove());
          
          return;
        }
      } catch (e) {
        console.error('Erro ao verificar status:', e);
      }
      
      await new Promise(r => setTimeout(r, 1000));
      attempts++;
    }
    
    appendInfo('<strong>Tempo esgotado.</strong><br>Não foi possível reconectar ao navegador.', false);
  }
  
  async function sendConversationHistory() {
    if (messages.length === 0) {
      appendInfo('<strong>Assistente pronto!</strong><br>Envie uma mensagem para começar.', false);
      return;
    }
    
    appendInfo('<strong>Restaurando conversa...</strong><br>Enviando histórico para o assistente.', false);
    
    // Construir o histórico das mensagens
    const historyText = messages
      .filter(m => m.sender === 'user' || m.sender === 'bot')
      .map(m => {
        const role = m.sender === 'user' ? 'Usuário' : 'Assistente';
        return `${role}: ${m.text}`;
      })
      .join('\n\n');
    
    const contextMessage = `[CONTINUAÇÃO DE CONVERSA ANTERIOR]

Histórico da conversa:
${historyText}

[INSTRUÇÃO: Esta é uma continuação de uma conversa anterior. O usuário está retomando o chat. Responda normalmente à próxima mensagem do usuário, considerando todo o contexto acima.]`;
    
    try {
      // Enviar como contexto (sem esperar resposta)
      await fetch(API_URL + '/chat/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: contextMessage }),
      });
      
      appendInfo('<strong>Conversa restaurada!</strong><br>Você pode continuar de onde parou.', false);
    } catch (e) {
      console.error('Erro ao enviar histórico:', e);
      appendInfo('<strong>Assistente pronto!</strong><br>Não foi possível restaurar o histórico, mas você pode continuar.', false);
    }
  }

  async function sendMessage(text) {
    // Bloquear envio se navegador não estiver pronto
    if (!isReady) {
      appendError('Aguarde o navegador iniciar antes de enviar mensagens.');
      return;
    }
    
    appendBubble(text, 'user');
    chatInput.value = '';
    chatInput.disabled = true;
    chatSend.disabled = true;
    appendLoading();

    // Detectar se usuário perguntou sobre carência e enviar contexto
    const carenciaKeywords = ['carência', 'carencia', 'carências', 'carencias', 'parto', 'cobertura', 'coberto', 'coberta'];
    const isCarenciaQuestion = carenciaKeywords.some(keyword => text.toLowerCase().includes(keyword));
    
    if (isCarenciaQuestion) {
      try {
        // Carregar contexto de carência
        const carenciaResponse = await fetch('/carencia-contexto');
        if (carenciaResponse.ok) {
          const carenciaContext = await carenciaResponse.text();
          // Enviar contexto antes da pergunta
          await fetch(API_URL + '/chat/context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: carenciaContext }),
          });
        }
      } catch (e) {
        console.error('Erro ao carregar contexto de carência:', e);
      }
    }

    try {
      const res = await fetch(API_URL + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      removeLoading();
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        // Detectar erro de navegador fechado (502)
        if (res.status === 502 || (err.detail && err.detail.includes('navegador'))) {
          handleBrowserClosed();
        }
        appendError(err.detail || 'Erro ao comunicar com o assistente.');
        return;
      }
      const data = await res.json();
      appendBubble(data.reply || 'Sem resposta.', 'bot');
    } catch (e) {
      removeLoading();
      // Verificar se é erro de conexão (navegador pode estar fechado)
      if (e.message && (e.message.includes('fetch') || e.message.includes('network'))) {
        handleBrowserClosed();
      }
      appendError('Falha de conexão com o servidor.');
    } finally {
      chatInput.disabled = false;
      chatSend.disabled = false;
      chatInput.focus();
    }
  }

  function appendInfo(text, save = true) {
    const msg = document.createElement('div');
    msg.className = 'chat-message chat-message--bot';
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble--info';
    bubble.innerHTML = text;
    msg.appendChild(bubble);
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    if (save) {
      const temp = document.createElement('div');
      temp.innerHTML = text;
      messages.push({ text: temp.textContent || temp.innerText || text, sender: 'info', timestamp: Date.now() });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
  }

  // Carregar server_id salvo
  currentServerId = localStorage.getItem(SERVER_ID_KEY);

  // Carregar mensagens
  loadMessages();

  // Inicialização: começar bloqueado até verificar status
  setReady(false);

  // Inicialização: verificar status ou mostrar botão iniciar
  checkBrowserStatus();
  if (messages.length === 0) {
    showStartButton();
  }

  // Verificar status periodicamente para detectar se navegador foi fechado
  setInterval(checkBrowserStatus, 5000);

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  // Tornar funções globais para o nav.js
  window.chatModalCheckStatus = checkBrowserStatus;
  
  // Função para enviar contexto da página
  window.sendContextToGemini = async function(pageContent) {
    if (!isReady) {
      appendInfo('<strong>Aguardando navegador...</strong><br>Contexto será enviado quando o assistente estiver pronto.', false);
      // Aguardar até que o navegador esteja pronto
      const checkAndSend = setInterval(async () => {
        if (isReady) {
          clearInterval(checkAndSend);
          await actuallySendContext(pageContent);
        }
      }, 1000);
      // Timeout de 30 segundos
      setTimeout(() => clearInterval(checkAndSend), 30000);
      return;
    }
    
    await actuallySendContext(pageContent);
  };
  
  async function actuallySendContext(pageContent) {
    // Bloquear envio se navegador não estiver pronto
    if (!isReady) {
      appendError('Aguarde o navegador iniciar antes de enviar contexto.');
      return;
    }
    
    // Adicionar mensagem no chat indicando que contexto foi enviado
    appendInfo('<strong>Contexto da página enviado</strong><br>O assistente agora tem acesso ao conteúdo desta página.', false);
    
    try {
      const res = await fetch(API_URL + '/chat/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: pageContent }),
      });
      
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        appendError(err.detail || 'Erro ao enviar contexto.');
        return;
      }
      
      const data = await res.json();
      if (data.success) {
        // Contexto enviado com sucesso - não adicionar resposta do bot
        console.log('Contexto enviado com sucesso');
      }
    } catch (e) {
      appendError('Falha de conexão ao enviar contexto.');
    }
  }
})();
