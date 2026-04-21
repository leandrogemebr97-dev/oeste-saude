"""
load_rol.py
-----------
Carrega a tabela de Correlação TUSS x Rol ANS (XLSX) no banco SQLite.

Uso:
    python app/load_rol.py
"""

import sqlite3
import re
import pandas as pd
from pathlib import Path

BASE  = Path(__file__).parent.parent
XLSX  = BASE / "data" / "pdfs" / "CorrelaoTUSS.202409Rol.2021_TUSS202601_RN652.2025.xlsx"
DB    = BASE / "data" / "rol.db"


def clean(val):
    if val is None or (isinstance(val, float) and __import__('math').isnan(val)):
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()


def load_procedimentos(conn: sqlite3.Connection):
    print("→ Lendo XLSX...")

    # Cabeçalho real está na linha 6 (0-indexed)
    df_raw = pd.read_excel(XLSX, header=6)

    # Renomeia colunas para nomes limpos
    col_map = {
        df_raw.columns[0]:  "codigo_tuss",
        df_raw.columns[1]:  "descricao_tuss",
        df_raw.columns[2]:  "correlacao",
        df_raw.columns[3]:  "procedimento",
        df_raw.columns[4]:  "rn",
        df_raw.columns[5]:  "vigencia",
        df_raw.columns[6]:  "od",
        df_raw.columns[7]:  "amb",
        df_raw.columns[8]:  "hco",
        df_raw.columns[9]:  "hso",
        df_raw.columns[10]: "pac",
        df_raw.columns[11]: "dut",
        df_raw.columns[12]: "subgrupo",
        df_raw.columns[13]: "grupo",
        df_raw.columns[14]: "capitulo",
    }
    df = df_raw.rename(columns=col_map)

    # Limpa todas as células
    for col in df.columns:
        df[col] = df[col].apply(clean)

    # Remove linhas completamente vazias
    df = df[df.apply(lambda r: any(v for v in r), axis=1)]

    # Remove linhas que são repetição de cabeçalho
    df = df[~df["codigo_tuss"].str.upper().isin(["CÓDIGO", "CODIGO", ""])]

    # Mantém SIM e NÃO — remove apenas linhas sem correlação definida
    df = df[df["correlacao"].str.upper().isin(["SIM", "NÃO", "NAO"])]

    # Normaliza correlacao para SIM/NAO
    df["correlacao"] = df["correlacao"].str.upper().str.replace("NÃO", "NAO")

    df = df.reset_index(drop=True)

    print(f"  → {len(df)} registros encontrados")

    # Salva no banco
    df.to_sql("procedimentos", conn, if_exists="replace", index=False)

    # Índices para busca rápida
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proc_codigo ON procedimentos(codigo_tuss)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proc_nome   ON procedimentos(procedimento)")
    conn.commit()

    print(f"  ✓ {len(df)} procedimentos salvos")


if __name__ == "__main__":
    # Remove banco antigo
    if DB.exists():
        DB.unlink()
        print(f"Banco anterior removido: {DB}")

    print(f"Banco: {DB}\n")
    conn = sqlite3.connect(DB)

    load_procedimentos(conn)

    conn.close()
    print("\n✅ rol.db gerado com sucesso!")
