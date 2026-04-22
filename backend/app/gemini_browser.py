"""
gemini_browser.py — automação do Gemini web via Playwright + CDP.

Conecta-se a uma instância do Chrome já aberta (com --remote-debugging-port=9222).
Navega até https://gemini.google.com/, envia mensagens e captura as respostas renderizadas na página.
"""

import time
import threading
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright

# Lock global para garantir thread-safety no acesso ao navegador
_browser_lock = threading.Lock()

GEMINI_URL = "https://gemini.google.com/"
CDP_URL = "http://127.0.0.1:9222"
USER_DATA_DIR = Path(__file__).parent.parent / ".chrome_data"

# JavaScript para extrair TODAS as mensagens do DOM do Gemini (baseado nos seletores reais)
_EXTRACT_ALL_MESSAGES_JS = """
(() => {
  const results = [];
  // Seletores específicos do Gemini web
  const modelResponses = document.querySelectorAll('model-response');
  for (const mr of modelResponses) {
    const content = mr.querySelector('message-content, .markdown, .markdown-main-panel');
    if (content) {
      const txt = (content.innerText || content.textContent || '').trim();
      if (txt.length > 5) results.push(txt);
    }
  }
  // Fallback: busca elementos com classe de resposta
  if (results.length === 0) {
    const altResponses = document.querySelectorAll('[class*="response"], [class*="model-response"]');
    for (const ar of altResponses) {
      // Evita elementos de usuário
      if (!ar.closest('[class*="user"]')) {
        const txt = (ar.innerText || ar.textContent || '').trim();
        if (txt.length > 5) results.push(txt);
      }
    }
  }
  return results;
})()
"""

# JavaScript para contar mensagens do bot (usado para detectar quando nova resposta chega)
_COUNT_BOT_MSGS_JS = """
(() => {
  let count = 0;
  const modelResponses = document.querySelectorAll('model-response');
  for (const mr of modelResponses) {
    const content = mr.querySelector('message-content, .markdown');
    if (content) {
      const txt = (content.innerText || content.textContent || '').trim();
      if (txt.length > 5) count++;
    }
  }
  return count;
})()
"""


class GeminiBrowser:
    """Controla uma aba do Chrome apontada para gemini.google.com."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None
        self._connected = False

    # ──────────────────────────────────────────
    # Lifecycle (sync - rodam em thread separada)
    # ──────────────────────────────────────────

    def start(self) -> None:
        """Inicia Chromium embutido do Playwright."""
        # Usar lock global para garantir thread-safety
        with _browser_lock:
            print("[GeminiBrowser] Iniciando Chromium embutido do Playwright...")
            self._pw = sync_playwright().start()

            try:
                # Iniciar Chromium embutido do Playwright (não Chrome do sistema)
                self._browser = self._pw.chromium.launch(
                    headless=False,
                    args=[
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                # Criar contexto com user data dir
                context = self._browser.new_context()
                self._page = context.new_page()
                self._page.goto(GEMINI_URL, wait_until="domcontentloaded")
                self._connected = True
                print("[GeminiBrowser] Chromium embutido iniciado com sucesso.")
            except Exception as e:
                print(f"[GeminiBrowser] Erro ao iniciar Chromium: {e}")
                raise

    def _find_or_create_gemini_tab(self, ctx):
        """Reutiliza aba do Gemini se já existir; senão cria uma nova."""
        for p in ctx.pages:
            if GEMINI_URL in p.url:
                p.bring_to_front()
                return p
        p = ctx.new_page()
        p.goto(GEMINI_URL, wait_until="domcontentloaded")
        return p

    def ensure_ready(self) -> None:
        if not self._connected:
            self.start()
        if self._page.is_closed():
            self._page = self._browser.new_page()
            self._page.goto(GEMINI_URL, wait_until="domcontentloaded")

    def close(self) -> None:
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
        self._connected = False

    # ──────────────────────────────────────────
    # Interação
    # ──────────────────────────────────────────

    def send(self, text: str, timeout: float = 60.0) -> str:
        """Envia *text* no Gemini web e retorna a última resposta do bot."""
        # Usar lock global para garantir thread-safety
        with _browser_lock:
            self.ensure_ready()
            p = self._page

            # 1) Conta mensagens do bot antes
            before = p.evaluate(_COUNT_BOT_MSGS_JS)
            print(f"[GeminiBrowser] Mensagens bot antes: {before}")

            # 2) Localiza o campo de input e envia
            self._type_and_submit(text)

            # 3) Espera nova mensagem do bot aparecer
            deadline = time.time() + timeout
            while time.time() < deadline:
                time.sleep(1.5)
                after = p.evaluate(_COUNT_BOT_MSGS_JS)
                print(f"[GeminiBrowser] Mensagens bot agora: {after}")
                if after > before:
                    # Espera mais tempo para o streaming terminar
                    time.sleep(3.0)
                    
                    # Verifica se a resposta está estável (não mudando mais)
                    last_text = None
                    stable_count = 0
                    for _ in range(5):
                        current_text = self._extract_last_bot_text()
                        if current_text == last_text:
                            stable_count += 1
                        else:
                            stable_count = 0
                            last_text = current_text
                        if stable_count >= 2:
                            break
                        time.sleep(1.0)
                    
                    return self._extract_last_bot_text()

            # 4) Fallback
            result = self._extract_last_bot_text()
            return result or "(Sem resposta — timeout)"

    def _type_and_submit(self, text: str) -> None:
        p = self._page
        # Gemini usa <textarea> ou contenteditable — tentamos vários seletores
        selectors = [
            'textarea[placeholder]',
            'textarea',
            '[contenteditable="true"]',
            'rich-textarea',
            '[data-test-id="input"]',
        ]
        input_el = None
        for sel in selectors:
            try:
                loc = p.locator(sel).first
                if loc.is_visible(timeout=2000):
                    input_el = loc
                    break
            except Exception:
                continue

        if not input_el:
            raise RuntimeError(
                "Não encontrei o campo de texto do Gemini. "
                "Possíveis causas: (1) Chrome não está aberto com --remote-debugging-port=9222; "
                "(2) A página do Gemini não carregou ou exige login. "
                "Feche todos os Chrome e reabra com: "
                'chrome.exe --remote-debugging-port=9222'
            )

        input_el.fill(text)
        time.sleep(0.3)
        # Gemini às vezes precisa de Enter duplo ou clique no botão enviar
        input_el.press("Enter")
        time.sleep(0.5)
        # tenta clicar no botão de enviar como fallback
        try:
            send_btn = p.locator('button[aria-label*="enviar"], button[aria-label*="send"], [data-test-id="send-button"]').first
            if send_btn.is_visible(timeout=500):
                send_btn.click()
        except Exception:
            pass

    def _extract_last_bot_text(self) -> Optional[str]:
        """Usa JavaScript injection para extrair o texto da última resposta do bot."""
        p = self._page
        try:
            msgs = p.evaluate(_EXTRACT_ALL_MESSAGES_JS)
            if isinstance(msgs, list) and msgs:
                return msgs[-1].strip()
        except Exception as e:
            print(f"[GeminiBrowser] Erro JS extraction: {e}")

        # Fallbacks com seletores CSS diretos
        css_fallbacks = [
            '[message-author="model"]',
            '.model-response-text',
            '.message-content',
            '[data-test-id="response"]',
            '.response-container',
            '.bot-message',
        ]
        for sel in css_fallbacks:
            try:
                count = p.locator(sel).count()
                if count > 0:
                    txt = p.locator(sel).nth(count - 1).inner_text()
                    if txt and txt.strip():
                        return txt.strip()
            except Exception:
                continue
        return None


# singleton para reutilizar a mesma aba entre requisições
_browser_instance: Optional[GeminiBrowser] = None


def get_browser() -> GeminiBrowser:
    global _browser_instance
    if _browser_instance is None or not _browser_instance._connected:
        _browser_instance = GeminiBrowser()
        _browser_instance.start()
    return _browser_instance
