"""
gemini_browser.py — automação do Gemini web via Playwright.

Roda o Playwright em uma thread dedicada para evitar conflitos com
greenlets do uvicorn/gunicorn.
"""

import time
import threading
import queue
from typing import Optional
from playwright.sync_api import sync_playwright

GEMINI_URL = "https://gemini.google.com/"

_EXTRACT_ALL_MESSAGES_JS = """
(() => {
  const results = [];
  const modelResponses = document.querySelectorAll('model-response');
  for (const mr of modelResponses) {
    const content = mr.querySelector('message-content, .markdown, .markdown-main-panel');
    if (content) {
      const txt = (content.innerText || content.textContent || '').trim();
      if (txt.length > 5) results.push(txt);
    }
  }
  if (results.length === 0) {
    const alt = document.querySelectorAll('[class*="response"], [class*="model-response"]');
    for (const ar of alt) {
      if (!ar.closest('[class*="user"]')) {
        const txt = (ar.innerText || ar.textContent || '').trim();
        if (txt.length > 5) results.push(txt);
      }
    }
  }
  return results;
})()
"""

_COUNT_BOT_MSGS_JS = """
(() => {
  let count = 0;
  const modelResponses = document.querySelectorAll('model-response');
  for (const mr of modelResponses) {
    const content = mr.querySelector('message-content, .markdown');
    if (content && (content.innerText || '').trim().length > 5) count++;
  }
  return count;
})()
"""


class _BrowserWorker(threading.Thread):
    """Thread dedicada que possui o Playwright e processa comandos via fila."""

    def __init__(self):
        super().__init__(daemon=True, name="playwright-worker")
        self._cmd_q: queue.Queue = queue.Queue()
        self._pw = None
        self._browser = None
        self._page = None
        self.connected = False
        self.start()

    def run(self):
        """Loop principal da thread — inicia Playwright e processa comandos."""
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=False,
                args=["--no-first-run", "--no-default-browser-check"],
            )
            ctx = self._browser.new_context()
            self._page = ctx.new_page()
            self._page.goto(GEMINI_URL, wait_until="domcontentloaded")
            self.connected = True
            print("[BrowserWorker] Chromium iniciado.")
        except Exception as e:
            print(f"[BrowserWorker] Falha ao iniciar: {e}")
            self.connected = False

        while True:
            try:
                cmd, args, result_q = self._cmd_q.get(timeout=1)
            except queue.Empty:
                continue

            if cmd == "stop":
                break

            try:
                result = getattr(self, f"_cmd_{cmd}")(*args)
                result_q.put(("ok", result))
            except Exception as e:
                result_q.put(("err", e))

        # Cleanup
        try:
            self._browser.close()
            self._pw.stop()
        except Exception:
            pass

    def _call(self, cmd: str, *args, timeout: float = 90.0):
        """Envia comando para a thread e aguarda resultado."""
        result_q: queue.Queue = queue.Queue()
        self._cmd_q.put((cmd, args, result_q))
        status, value = result_q.get(timeout=timeout)
        if status == "err":
            raise value
        return value

    # ── Comandos executados dentro da thread ──────────────────

    def _cmd_send(self, text: str, timeout: float) -> str:
        p = self._page
        if p.is_closed():
            ctx = self._browser.new_context()
            self._page = ctx.new_page()
            self._page.goto(GEMINI_URL, wait_until="domcontentloaded")
            p = self._page

        before = p.evaluate(_COUNT_BOT_MSGS_JS)

        # Localiza input
        input_el = None
        for sel in ['textarea[placeholder]', 'textarea', '[contenteditable="true"]', 'rich-textarea']:
            try:
                loc = p.locator(sel).first
                if loc.is_visible(timeout=2000):
                    input_el = loc
                    break
            except Exception:
                continue

        if not input_el:
            raise RuntimeError("Campo de texto do Gemini não encontrado.")

        input_el.fill(text)
        time.sleep(0.3)
        input_el.press("Enter")
        time.sleep(0.5)

        # Botão enviar (fallback)
        try:
            btn = p.locator('button[aria-label*="enviar"], button[aria-label*="send"]').first
            if btn.is_visible(timeout=500):
                btn.click()
        except Exception:
            pass

        # Aguarda resposta
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(1.5)
            after = p.evaluate(_COUNT_BOT_MSGS_JS)
            if after > before:
                time.sleep(3.0)
                # Aguarda estabilizar
                last = None
                stable = 0
                for _ in range(5):
                    cur = self._extract_last()
                    if cur == last:
                        stable += 1
                    else:
                        stable = 0
                        last = cur
                    if stable >= 2:
                        break
                    time.sleep(1.0)
                return self._extract_last() or "(Sem resposta)"

        return self._extract_last() or "(Timeout)"

    def _extract_last(self) -> Optional[str]:
        p = self._page
        try:
            msgs = p.evaluate(_EXTRACT_ALL_MESSAGES_JS)
            if isinstance(msgs, list) and msgs:
                return msgs[-1].strip()
        except Exception:
            pass
        for sel in ['[message-author="model"]', '.model-response-text', '.message-content']:
            try:
                n = p.locator(sel).count()
                if n > 0:
                    txt = p.locator(sel).nth(n - 1).inner_text()
                    if txt and txt.strip():
                        return txt.strip()
            except Exception:
                continue
        return None

    # ── API pública (chamada de qualquer thread) ───────────────

    def send(self, text: str, timeout: float = 60.0) -> str:
        return self._call("send", text, timeout, timeout=timeout + 10)

    def stop(self):
        result_q: queue.Queue = queue.Queue()
        self._cmd_q.put(("stop", [], result_q))


# ── Singleton ─────────────────────────────────────────────────
_worker: Optional[_BrowserWorker] = None
_worker_lock = threading.Lock()


def get_browser() -> _BrowserWorker:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.connected or not _worker.is_alive():
            _worker = _BrowserWorker()
            # Aguarda inicialização (máx 15s)
            for _ in range(30):
                if _worker.connected:
                    break
                time.sleep(0.5)
        return _worker


# Compatibilidade com código existente
_browser_instance = None
