"""
load_dut.py
-----------
Extrai as Diretrizes de Utilização (DUT) do Anexo II em PDF.
Estratégia:
  - Usa os títulos oficiais do sumário como âncoras no texto
  - Para DUTs com tabelas (substância/indicação), extrai via extract_tables()
  - Sub-itens (54.1, 65.1...) são salvos como registros separados

Uso:
    python app/load_dut.py
"""

import sqlite3
import re
import pdfplumber
from pathlib import Path

BASE = Path(__file__).parent.parent
PDF  = BASE / "data" / "pdfs" / "Anexo_II_DUT_2021_RN_465.2021_RN628.2025_RN629.2025.pdf"
DB   = BASE / "data" / "rol.db"

PAGINA_INICIO = 8  # 0-indexed

# Títulos oficiais — chave: número, valor: título exato como aparece no PDF
TITULOS_DUT = {
    "1":   "ABLAÇÃO POR RADIOFREQUÊNCIA/CRIOABLAÇÃO DO CÂNCER PRIMÁRIO HEPÁTICO",
    "2":   "ACILCARNITINAS, PERFIL QUALITATIVO E/OU QUANTITATIVO COM ESPECTROMETRIA DE MASSA EM TANDEM",
    "3":   "ANGIOTOMOGRAFIA CORONARIANA",
    "4":   "ANTICORPOS ANTI PEPTÍDEO CÍCLICO CITRULINADO - IGG (ANTI CCP)",
    "5":   "AUDIOMETRIA VOCAL COM MENSAGEM COMPETITIVA",
    "6":   "AVIDEZ DE IGG PARA TOXOPLASMOSE",
    "7":   "BIÓPSIA PERCUTÂNEA À VÁCUO GUIADA POR RAIO X",
    "8":   "BLOQUEIO COM TOXINA BOTULÍNICA TIPO A",
    "9":   "BRAF",
    "10":  "CINTILOGRAFIA DO MIOCÁRDIO",
    "11":  "CIRURGIA DE ESTERILIZAÇÃO FEMININA",
    "12":  "CIRURGIA DE ESTERILIZAÇÃO MASCULINA",
    "13":  "CIRURGIA REFRATIVA",
    "14":  "CITOMEGALOVÍRUS",
    "15":  "COLOBOMA",
    "16":  "COLOCAÇÃO DE BANDA GÁSTRICA",
    "17":  "CORDOTOMIA-MIELOTOMIAS POR RADIOFREQUÊNCIA",
    "18":  "ABDOMINOPLASTIA",
    "19":  "DÍMERO-D",
    "20":  "ECODOPPLERCARDIOGRAMA FETAL",
    "21":  "EGFR",
    "22":  "ELETROFORESE DE PROTEÍNAS DE ALTA RESOLUÇÃO",
    "23":  "EMBOLIZAÇÃO DE ARTÉRIA UTERINA",
    "24":  "ESTIMULAÇÃO ELÉTRICA TRANSCUTÂNEA",
    "25":  "FATOR V LEIDEN",
    "26":  "GALACTOSE-1-FOSFATO URIDILTRANSFERASE",
    "27":  "GASTROPLASTIA",
    "28":  "HEPATITE B",
    "29":  "HEPATITE C",
    "30":  "HER-2",
    "31":  "HIV, GENOTIPAGEM",
    "32":  "HLA-B27",
    "33":  "IMPLANTE COCLEAR",
    "34":  "IMPLANTE DE ANEL INTRAESTROMAL",
    "35":  "IMPLANTE DE CARDIODESFIBRILADOR IMPLANTÁVEL",
    "36":  "IMPLANTE DE CARDIODESFIBRILADOR MULTISSÍTIO",
    "37":  "IMPLANTE DE ELETRODOS E/OU GERADOR PARA ESTIMULAÇÃO MEDULAR",
    "38":  "IMPLANTE DE ELETRODOS E/OU GERADOR PARA ESTIMULAÇÃO CEREBRAL",
    "39":  "IMPLANTE DE GERADOR PARA NEUROESTIMULAÇÃO",
    "40":  "IMPLANTE DE MARCA-PASSO BICAMERAL",
    "41":  "IMPLANTE DE MARCA-PASSO MONOCAMERAL",
    "42":  "IMPLANTE DE MARCAPASSO MULTISSÍTIO",
    "43":  "IMPLANTE DE MONITOR DE EVENTOS",
    "44":  "IMPLANTE DE PRÓTESE AUDITIVA ANCORADA NO OSSO",
    "45":  "IMPLANTE INTRA-TECAL DE BOMBAS",
    "46":  "IMPLANTE INTRAVÍTREO DE POLÍMERO FARMACOLÓGICO",
    "47":  "IMUNOFIXAÇÃO PARA PROTEÍNAS",
    "48":  "INCONTINÊNCIA URINÁRIA",
    "49":  "INIBIDOR DOS FATORES DA HEMOSTASIA",
    "50":  "K-RAS",
    "51":  "LASERTERAPIA PARA O TRATAMENTO DA MUCOSITE",
    "52":  "MAMOGRAFIA DIGITAL",
    "53":  "MAPEAMENTO ELETROANATÔMICO CARDÍACO",
    "54":  "MEDICAMENTOS PARA O CONTROLE DE EFEITOS ADVERSOS",
    "55":  "MICROCIRURGIA",
    "56":  "MONITORIZAÇÃO AMBULATORIAL DA PRESSÃO ARTERIAL - MAPA (24 HORAS)",
    "57":  "N-RAS",
    "58":  "OXIGENOTERAPIA HIPERBÁRICA",
    "59":  "PANTOFOTOCOAGULAÇÃO A LASER",
    "60":  "PET-CT ONCOLÓGICO",
    "61":  "PROTROMBINA",
    "62":  "RIZOTOMIA PERCUTÂNEA",
    "63":  "SUCCINIL ACETONA",
    "64":  "TERAPIA ANTINEOPLÁSICA ORAL",
    "65":  "TERAPIA IMUNOBIOLÓGICA ENDOVENOSA",
    "66":  "TERMOTERAPIA TRANSPUPILAR",
    "67":  "TESTE DE INCLINAÇÃO ORTOSTÁTICA",
    "68":  "TESTE ERGOMÉTRICO",
    "69":  "TOMOGRAFIA DE COERÊNCIA ÓPTICA",
    "70":  "TRANSPLANTE ALOGÊNICO DE MEDULA ÓSSEA",
    "71":  "TRANSPLANTE AUTÓLOGO DE MEDULA ÓSSEA",
    "72":  "TRATAMENTO CIRÚRGICO DA EPILEPSIA",
    "73":  "TRATAMENTO DA HIPERATIVIDADE VESICAL",
    "74":  "TRATAMENTO OCULAR QUIMIOTERÁPICO",
    "75":  "ULTRASSONOGRAFIA OBSTÉTRICA MORFOLÓGICA",
    "76":  "ULTRASSONOGRAFIA OBSTÉTRICA COM TRANSLUCÊNCIA NUCAL",
    "77":  "VITAMINA E",
    "78":  "ADEQUAÇÃO DO MEIO BUCAL",
    "79":  "APLICAÇÃO DE CARIOSTÁTICO",
    "80":  "APLICAÇÃO DE SELANTE",
    "81":  "BIÓPSIA DE BOCA",
    "82":  "BIÓPSIA DE GLÂNDULA SALIVAR",
    "83":  "BIÓPSIA DE LÁBIO",
    "84":  "BIÓPSIA DE LÍNGUA",
    "85":  "BIÓPSIA DE MANDÍBULA",
    "86":  "CONDICIONAMENTO EM ODONTOLOGIA",
    "87":  "TRATAMENTO CIRÚRGICO DE TUMORES BENIGNOS ODONTOGÊNICOS",
    "88":  "TRATAMENTO CIRÚRGICO DE TUMORES BENIGNOS DE TECIDOS ÓSSEOS",
    "89":  "REABILITAÇÃO COM COROA DE ACETATO",
    "90":  "COROA UNITÁRIA PROVISÓRIA",
    "91":  "EXÉRESE DE PEQUENOS CISTOS",
    "92":  "REABILITAÇÃO COM COROA TOTAL DE CERÔMERO",
    "93":  "REABILITAÇÃO COM COROA TOTAL METÁLICA",
    "94":  "REABILITAÇÃO COM NÚCLEO METÁLICO FUNDIDO",
    "95":  "REABILITAÇÃO COM RESTAURAÇÃO METÁLICA FUNDIDA",
    "96":  "REDUÇÃO DE LUXAÇÃO DA ATM",
    "97":  "SUTURA DE FERIDA",
    "98":  "TRATAMENTO CIRÚRGICO DAS FÍSTULAS BUCO",
    "99":  "TRATAMENTO CIRÚRGICO DOS TUMORES BENIGNOS DE TECIDOS MOLES",
    "100": "TRATAMENTO RESTAURADOR ATRAUMÁTICO",
    "101": "TUNELIZAÇÃO",
    "102": "CONSULTA COM FISIOTERAPEUTA",
    "103": "CONSULTA COM NUTRICIONISTA",
    "104": "SESSÃO COM FONOAUDIÓLOGO",
    "105": "SESSÃO COM PSICÓLOGO",
    "106": "SESSÃO COM PSICÓLOGO E/OU TERAPEUTA OCUPACIONAL",
    "107": "SESSÃO COM TERAPEUTA OCUPACIONAL",
    "108": "SESSÃO DE PSICOTERAPIA",
    "109": "ATENDIMENTO/ACOMPANHAMENTO EM HOSPITAL-DIA",
    "110": "ANÁLISE MOLECULAR DE DNA",
    "111": "VÍRUS ZIKA – POR PCR",
    "112": "VÍRUS ZIKA – IGM",
    "113": "VÍRUS ZIKA – IGG",
    "114": "ALK",
    "115": "ANGIO-RM ARTERIAL DE MEMBRO INFERIOR",
    "116": "ANGIOTOMOGRAFIA ARTERIAL DE MEMBRO INFERIOR",
    "117": "AQUAPORINA 4",
    "118": "CINTILOGRAFIA DE PERFUSÃO CEREBRAL",
    "119": "ELASTOGRAFIA HEPÁTICA ULTRASSÔNICA",
    "120": "FOCALIZAÇÃO ISOELÉTRICA DE TRANSFERRINA",
    "121": "RADIAÇÃO PARA CROSS LINKING CORNEANO",
    "122": "REFLUXO VÉSICO-URETERAL",
    "123": "RM - FLUXO LIQUÓRICO",
    "124": "TERAPIA IMUNOPROFILÁTICA COM PALIVIZUMABE",
    "125": "TOXOPLASMOSE",
    "126": "SARS-CoV-2",
    "127": "PROCALCITONINA",
    "128": "PESQUISA RÁPIDA PARA INFLUENZA",
    "129": "PCR EM TEMPO REAL PARA INFLUENZA",
    "130": "PESQUISA RÁPIDA PARA VÍRUS SINCICIAL",
    "131": "PCR EM TEMPO REAL PARA VÍRUS SINCICIAL",
    "132": "SARS-COV-2 (CORONAVÍRUS COVID-19) - PESQUISA DE ANTICORPOS",
    "133": "ARTROPLASTIA DISCAL",
    "134": "CALPROTECTINA",
    "135": "CONSULTA COM ENFERMEIRO OBSTETRA",
    "136": "CONSULTA/AVALIAÇÃO COM FONOAUDIÓLOGO",
    "137": "CONSULTA/AVALIAÇÃO COM PSICÓLOGO",
    "138": "CONSULTA/AVALIAÇÃO COM TERAPEUTA OCUPACIONAL",
    "139": "RAZÃO DO TESTE SFLT",
    "140": "ENSAIO PARA DOSAGEM DA LIBERAÇÃO DE INTERFERON",
    "141": "ENTEROSCOPIA DO INTESTINO DELGADO",
    "142": "FLT3",
    "143": "IMPLANTE TRANSCATETER DE PRÓTESE VALVAR",
    "144": "OSTEOTOMIA DA MANDÍBULA",
    "145": "PARTO CESARIANO",
    "146": "PD-L1",
    "147": "RADIOTERAPIA INTRA-OPERATÓRIA",
    "148": "TERAPIA POR PRESSÃO NEGATIVA",
    "149": "CIRURGIA ANTIGLAUCOMATOSA",
    "150": "TESTE SARS-COV-2",
    "151": "ELASTASE PANCREÁTICA FECAL",
    "152": "TESTE DE PROVOCAÇÃO ORAL COM ALIMENTOS",
    "153": "TERAPIA COM ALFACERLIPONASE",
    "154": "APLICAÇÃO DE CONTRACEPTIVO HORMONAL INJETÁVEL",
    "155": "RADIOEMBOLIZAÇÃO HEPÁTICA",
    "156": "BRCA1 E BRCA2, PESQUISA DE MUTAÇÃO SOMÁTICA",
    "157": "TESTE PARA DETECÇÃO DO VÍRUS MONKEYPOX",
    "158": "TERAPIA MEDICAMENTOSA INJETÁVEL AMBULATORIAL",
    "159": "TERAPIA AVANÇADA PARA O TRATAMENTO DA ATROFIA MUSCULAR ESPINHAL",
    "160": "TESTE DE DEFICIÊNCIA DE RECOMBINAÇÃO HOMÓLOGA",
    "161": "TERAPIA COM ALFAGALSIDASE",
    "162": "MONITORIZAÇÃO AMBULATORIAL DA PRESSÃO ARTERIAL DE 5 DIAS",
    "163": "TERAPIA INTRAVENOSA COM ÁCIDO ZOLEDRÔNICO",
    "164": "ABLAÇÃO POR RADIOFREQUÊNCIA PERCUTÂNEA DE METÁSTASES HEPÁTICAS",
    "165": "ECOBRONCOSCOPIA COM PUNÇÃO ASPIRATIVA",
    "166": "FECHAMENTO DO APÊNDICE ATRIAL ESQUERDO",
    "167": "TESTE DE FLUXO LATERAL PARA DETECÇÃO DE LIPOARABINOMANANO",
    "168": "TESTE DE HIBRIDIZAÇÃO COM SONDA EM LINHA (LPA 1",
    "169": "TESTE DE HIBRIDIZAÇÃO COM SONDA EM LINHA (LPA 2",
    "170": "IMPLANTE SUBDÉRMICO HORMONAL PARA CONTRACEPÇÃO",
    "171": "INSTALAÇÃO E MANUTENÇÃO DE DISPOSITIVO DE ASSISTÊNCIA VENTRICULAR",
    "172": "NTRK",
    "173": "PROSTATECTOMIA RADICAL ASSISTIDA POR ROBÔ",
}


def clean(val):
    if not val:
        return ""
    return re.sub(r"\s+", " ", str(val)).strip()


def extrair_texto_completo(pdf_path: Path) -> str:
    texto = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages[PAGINA_INICIO:], start=PAGINA_INICIO + 1):
            print(f"  Lendo página {i}/{total}", end="\r")
            t = page.extract_text()
            if t:
                texto.append(t)
    print()
    return "\n".join(texto)


def extrair_tabelas_dut(pdf_path: Path, nums_com_tabela: set) -> dict:
    """Extrai tabelas das DUTs que têm estrutura tabular (ex: 54, 65, 158)."""
    tabelas = {}
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        texto_acumulado = ""
        dut_atual = None

        for i, page in enumerate(pdf.pages[PAGINA_INICIO:], start=PAGINA_INICIO):
            t = page.extract_text() or ""

            # Detecta início de DUT com tabela
            for num in nums_com_tabela:
                titulo = TITULOS_DUT.get(num, "")
                palavras = titulo.split()[:3]
                if any(p in t for p in palavras):
                    dut_atual = num
                    break

            if dut_atual and dut_atual in nums_com_tabela:
                tbls = page.extract_tables()
                if tbls:
                    if dut_atual not in tabelas:
                        tabelas[dut_atual] = []
                    for tbl in tbls:
                        for row in tbl:
                            cleaned = [clean(c) for c in row if clean(c)]
                            if cleaned:
                                tabelas[dut_atual].append(cleaned)

    return tabelas


def limpar_inicio_criterios(conteudo: str, num: str) -> str:
    """
    Remove o resto do título que vaza para o início dos critérios.
    O conteúdo real começa sempre com '1.' ou com um sub-item como '54.1' ou '65.1'.
    """
    # Padrão: conteúdo real começa com número de critério ou sub-item
    inicio = re.search(
        rf'(?:^|\s)(?:{re.escape(num)}\.\d+[\s\-]|1\.\s+[A-ZÁÉÍÓÚ])',
        conteudo
    )
    if inicio:
        return conteudo[inicio.start():].strip()

    # Fallback: remove tudo até o primeiro "Cobertura obrigatória" ou "1."
    m = re.search(r'(?:1\.\s|Cobertura obrigatória)', conteudo, re.IGNORECASE)
    if m:
        return conteudo[m.start():].strip()

    return conteudo


def parsear_duts(texto: str) -> list[dict]:
    nums_ordenados = sorted(TITULOS_DUT.keys(), key=lambda x: float(x))
    posicoes = []

    for num in nums_ordenados:
        titulo = TITULOS_DUT[num]
        palavras = titulo.split()[:3]

        for n_palavras in [3, 2, 1]:
            trecho = re.escape(" ".join(palavras[:n_palavras]))
            padrao = re.compile(
                rf'(?m)^{re.escape(num)}\.\s+["\u201c\u201d]?{trecho}',
                re.IGNORECASE
            )
            m = padrao.search(texto)
            if m:
                posicoes.append((num, m.start(), m.end()))
                break
        else:
            print(f"  ⚠ DUT {num} não localizada")

    duts = []
    for idx, (num, pos_inicio, pos_fim_titulo) in enumerate(posicoes):
        fim = posicoes[idx + 1][1] if idx + 1 < len(posicoes) else len(texto)
        conteudo = texto[pos_fim_titulo:fim].strip()

        # Normaliza espaços mas preserva quebras de linha
        conteudo = re.sub(r"[ \t]+", " ", conteudo)  # Apenas espaços/tab, não \n
        conteudo = re.sub(r"\n\s*\n", "\n\n", conteudo)  # Múltiplas quebras -> dupla
        conteudo = conteudo.strip()

        # Remove número de página solto no final
        conteudo = re.sub(r"\s+\d{1,3}\s*$", "", conteudo)

        # Limpa título que vaza para o início
        conteudo = limpar_inicio_criterios(conteudo, num)

        # Detecta se tem sub-itens (54.1, 65.1, 110.1 etc)
        tem_subitens = bool(re.search(rf'{re.escape(num)}\.\d+', conteudo))

        # Extrai RNs — do conteúdo E do trecho do título no texto
        trecho_titulo = texto[pos_inicio:pos_fim_titulo + 300]
        texto_busca_rn = trecho_titulo + " " + conteudo
        rns = re.findall(
            r'RN\s*(?:n[º°]?\s*)?(\d{3,4}/\d{4})',
            texto_busca_rn, re.IGNORECASE
        )
        rn_str = "; ".join(sorted(set(rns))) if rns else ""

        # Extrai vigência — do título e do conteúdo
        vigencias = re.findall(
            r'em vigor a partir de (\d{2}/\d{2}/\d{4})',
            texto_busca_rn, re.IGNORECASE
        )
        vigencia = vigencias[-1] if vigencias else ""

        # RN base 465/2021 para DUTs sem RN explícita (fazem parte da resolução original)
        if not rn_str:
            rn_str = "465/2021"

        duts.append({
            "numero":       num,
            "nome":         TITULOS_DUT[num],
            "criterios":    conteudo,
            "rn":           rn_str,
            "vigencia":     vigencia,
            "tem_subitens": 1 if tem_subitens else 0,
        })

    return duts


def salvar(conn: sqlite3.Connection, duts: list[dict]):
    conn.execute("DROP TABLE IF EXISTS dut")
    conn.execute("""
        CREATE TABLE dut (
            numero       TEXT PRIMARY KEY,
            nome         TEXT NOT NULL,
            criterios    TEXT,
            rn           TEXT,
            vigencia     TEXT,
            tem_subitens INTEGER DEFAULT 0
        )
    """)
    conn.executemany(
        "INSERT INTO dut (numero, nome, criterios, rn, vigencia, tem_subitens) VALUES (?,?,?,?,?,?)",
        [(d["numero"], d["nome"], d["criterios"], d["rn"], d["vigencia"], d["tem_subitens"]) for d in duts],
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dut_numero ON dut(numero)")
    conn.commit()
    print(f"  OK {len(duts)} diretrizes salvas")


if __name__ == "__main__":
    print(f"PDF: {PDF}")
    print(f"Banco: {DB}\n")

    print("Extraindo texto do PDF...")
    texto = extrair_texto_completo(PDF)

    print("Parseando diretrizes...")
    duts = parsear_duts(texto)
    print(f"  -> {len(duts)} diretrizes encontradas")

    conn = sqlite3.connect(DB)
    print("\nSalvando no banco...")
    salvar(conn, duts)
    conn.close()

    print("\nTabela DUT gerada com sucesso!")
    print(f"\nTotal: {len(duts)}/173 diretrizes")

    faltando = set(TITULOS_DUT.keys()) - {d["numero"] for d in duts}
    if faltando:
        print(f"Faltando: {sorted(faltando, key=float)}")

    sem_rn = [d["numero"] for d in duts if not d["rn"]]
    print(f"\nSem RN: {len(sem_rn)} -> {sem_rn[:10]}{'...' if len(sem_rn)>10 else ''}")

    com_subitens = [d["numero"] for d in duts if d["tem_subitens"]]
    print(f"Com sub-itens: {com_subitens}")

    # Amostra de qualidade
    print("\n--- Amostra de critérios (primeiros 120 chars) ---")
    for num in ["1", "10", "54", "65", "110", "158", "172", "173"]:
        d = next((x for x in duts if x["numero"] == num), None)
        if d:
            print(f"DUT {num}: {d['criterios'][:120]}")
