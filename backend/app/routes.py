import os
import sqlite3
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

load_dotenv()

# ID único gerado na inicialização do servidor (muda a cada reinício)
SERVER_INSTANCE_ID = str(int(time.time()))


DB   = Path(__file__).parent.parent / "data" / "rol.db"
REDE = Path(__file__).parent.parent / "data" / "rede.json"

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    if not DB.exists():
        raise HTTPException(
            status_code=503,
            detail="Banco não encontrado. Execute load_rol.py primeiro.",
        )
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: v for k, v in dict(row).items() if v not in (None, "")}


def agrupar_por_codigo(rows: list) -> list:
    """Retorna cada linha como item separado (não agrupa por código)"""
    items = []
    for row in rows:
        d = row_to_dict(row)
        tem_sim = d.get("correlacao", "").upper() == "SIM"
        items.append({
            "codigo_tuss":           d.get("codigo_tuss", ""),
            "descricao_tuss":        d.get("descricao_tuss", ""),
            "cobertura_obrigatoria": tem_sim,
            "segmentacao": {
                "amb": bool(d.get("amb")),
                "hco": bool(d.get("hco")),
                "hso": bool(d.get("hso")),
                "od":  bool(d.get("od")),
                "pac": bool(d.get("pac")),
            },
            "procedimentos_rol": [{
                "nome": d.get("procedimento", ""),
                "dut":  d.get("dut", ""),
                "rn":   d.get("rn", ""),
            }],
            "subgrupo":  d.get("subgrupo", ""),
            "grupo":     d.get("grupo", ""),
            "capitulo":  d.get("capitulo", ""),
        })
    return items


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/procedimentos", summary="Buscar procedimentos por nome ou código TUSS")
def buscar_procedimentos(
    q: str = Query(None, min_length=2, description="Nome parcial ou código TUSS"),
    limit: int = Query(20, ge=1, le=100),
):
    conn = get_conn()
    try:
        # Se não fornecer q, retorna os primeiros procedimentos
        if not q:
            cur = conn.execute(
                """
                SELECT * FROM procedimentos
                ORDER BY codigo_tuss, procedimento
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            items = agrupar_por_codigo(rows)
            return {"total": len(items), "items": items}

        q = q.strip()

        # Busca por código exato — retorna TODAS as linhas desse código
        cur = conn.execute(
            "SELECT * FROM procedimentos WHERE codigo_tuss = ?", (q,)
        )
        exact = cur.fetchall()
        if exact:
            items = agrupar_por_codigo(exact)
            return {"total": len(items), "items": items}

        # Busca por nome parcial ou código parcial
        cur = conn.execute(
            """
            SELECT * FROM procedimentos
            WHERE UPPER(procedimento)   LIKE UPPER(?)
               OR UPPER(descricao_tuss) LIKE UPPER(?)
               OR UPPER(codigo_tuss)    LIKE UPPER(?)
            ORDER BY codigo_tuss, procedimento
            LIMIT ?
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", limit),
        )
        rows = cur.fetchall()
        items = agrupar_por_codigo(rows)
        return {"total": len(items), "items": items}
    finally:
        conn.close()


@router.get("/procedimentos/{codigo}", summary="Detalhe completo de um código TUSS")
def detalhe_procedimento(codigo: str):
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT * FROM procedimentos WHERE codigo_tuss = ? ORDER BY procedimento",
            (codigo,),
        )
        rows = cur.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Código TUSS não encontrado")

        # Agrega todos os procedimentos do mesmo código TUSS para a tela de detalhes
        primeiro = row_to_dict(rows[0])
        tem_sim = any(r["correlacao"].upper() == "SIM" for r in rows if r["correlacao"])

        # Junta segmentação de todas as linhas
        segmentacao = {
            "amb": any(bool(r["amb"]) for r in rows),
            "hco": any(bool(r["hco"]) for r in rows),
            "hso": any(bool(r["hso"]) for r in rows),
            "od":  any(bool(r["od"])  for r in rows),
            "pac": any(bool(r["pac"]) for r in rows),
        }

        # Junta todos os procedimentos
        procedimentos = []
        vistos = set()
        for r in rows:
            proc = r["procedimento"]
            if proc and proc not in vistos:
                vistos.add(proc)
                procedimentos.append({
                    "nome": proc,
                    "dut": r["dut"] or "",
                    "rn": r["rn"] or "",
                })

        return {
            "codigo_tuss": primeiro.get("codigo_tuss", ""),
            "descricao_tuss": primeiro.get("descricao_tuss", ""),
            "cobertura_obrigatoria": tem_sim,
            "segmentacao": segmentacao,
            "procedimentos_rol": procedimentos,
            "subgrupo": primeiro.get("subgrupo", ""),
            "grupo": primeiro.get("grupo", ""),
            "capitulo": primeiro.get("capitulo", ""),
        }
    finally:
        conn.close()


@router.get("/dut/{numero}", summary="Diretriz de Utilização pelo número")
def buscar_dut(numero: str):
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT * FROM dut WHERE numero = ?", (numero,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"DUT {numero} não encontrada")
        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/rede", summary="Rede credenciada")
def rede_credenciada(
    q:     str = Query(None, description="Filtrar por cidade"),
    page:  int = Query(1, ge=1),
    limit: int = Query(4, ge=1, le=20),
):
    data = json.loads(REDE.read_text(encoding="utf-8"))
    if q:
        data = [u for u in data if q.lower() in u["cidade"].lower()]
    total = len(data)
    inicio = (page - 1) * limit
    fim    = inicio + limit
    return {
        "total":       total,
        "page":        page,
        "total_pages": -(-total // limit),  # ceil division
        "items":       data[inicio:fim],
    }


@router.get("/stats", summary="Totais do banco")
def stats():
    conn = get_conn()
    try:
        total_linhas = conn.execute("SELECT COUNT(*) FROM procedimentos").fetchone()[0]
        total_tuss   = conn.execute("SELECT COUNT(DISTINCT codigo_tuss) FROM procedimentos").fetchone()[0]
        total_procs  = conn.execute("SELECT COUNT(DISTINCT procedimento) FROM procedimentos").fetchone()[0]
        return {
            "codigos_tuss":          total_tuss,
            "procedimentos_rol":     total_procs,
            "total_correlacoes":     total_linhas,
            "fonte": "ANS — Correlação TUSS x Rol RN 465/2021 + RN 652/2025",
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# Chat Gemini
# ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str

@router.get("/chat/status", summary="Verificar se o navegador do Gemini está pronto")
def chat_status():
    try:
        from app.gemini_browser import _browser_instance
        print(f"[/chat/status] _browser_instance: {_browser_instance}")
        if _browser_instance:
            print(f"[/chat/status] _connected: {_browser_instance._connected}")
    except ImportError as exc:
        print(f"[/chat/status] Playwright não instalado: {exc}")
        return {"ready": False, "server_id": SERVER_INSTANCE_ID, "message": "Playwright não instalado"}
    
    if _browser_instance is None or not _browser_instance._connected:
        return {"ready": False, "server_id": SERVER_INSTANCE_ID, "message": "Navegador não iniciado"}
    
    return {"ready": True, "server_id": SERVER_INSTANCE_ID, "message": "Assistente pronto"}

@router.post("/chat/start", summary="Iniciar navegador do Gemini")
def start_browser():
    """Inicia o navegador do Gemini via Playwright."""
    try:
        from app.gemini_browser import get_browser
        browser = get_browser()
        return {"success": True, "message": "Navegador iniciado com sucesso"}
    except Exception as e:
        return {"success": False, "message": f"Erro ao iniciar navegador: {str(e)}"}

@router.post("/chat", summary="Enviar mensagem para o Gemini via navegador")
def chat_gemini(payload: ChatMessage):
    try:
        from app.gemini_browser import get_browser
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Playwright não instalado. Execute: pip install playwright && python -m playwright install chromium. Erro: {exc}"
        )

    try:
        browser = get_browser()
        reply = browser.send(payload.message)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro na automação do navegador: {str(e)}")

@router.post("/chat/context", summary="Enviar contexto da página para o Gemini (sem resposta)")
def chat_context(payload: ChatMessage):
    """Envia o conteúdo da página como contexto para o Gemini, sem aguardar resposta."""
    try:
        from app.gemini_browser import get_browser
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Playwright não instalado. Execute: pip install playwright && python -m playwright install chromium. Erro: {exc}"
        )

    try:
        browser = get_browser()
        
        # Verificar se a página está carregada
        if not browser._page or browser._page.is_closed():
            raise HTTPException(status_code=502, detail="Página do navegador não está disponível. Inicie o assistente novamente.")
        
        # Aguardar a página estar pronta
        try:
            browser._page.wait_for_load_state("domcontentloaded", timeout=2000)
        except:
            pass  # Se não conseguir aguardar, continua
        
        # Enviar mensagem com instrução para não responder
        context_message = f"""[CONTEXT DA PÁGINA - NÃO RESPONDA]

{payload.message}

[/CONTEXT]

INSTRUÇÃO IMPORTANTE: NÃO RESPONDA A ESTA MENSAGEM. Apenas guarde este contexto para a próxima conversa. Aguarde a próxima mensagem do usuário para responder."""
        
        browser.send(context_message)
        return {"success": True, "message": "Contexto enviado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro na automação do navegador: {str(e)}")
