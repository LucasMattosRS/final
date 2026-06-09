"""
Automacao de leitura de plantas eletricas/estruturais em PDF.

Fluxo:
  1. Agrupa PDFs por codigo de obra.
  2. Processa cada PDF.
  3. Detecta POSTE (P) e VÃO (V).
  4. Segue seta até destino e extrai informações.
"""

import os
import sys
import re
import logging
from collections import defaultdict

from config import (
    AUDITORIA_DIR,
    TOKENS_NAO_RECONHECIDOS_LOG,
    INPUT_DIR,
    OUTPUT_DIR,
    DEBUG_DIR,
    LOG_DIR,
    PDF_RENDER_SCALE,
    ASSOCIATION_RADIUS,
)

from src.work_number import get_work_number, get_sheet_number
from src.pdf_reader import read_pdf
from src.extractor_pv import extract_pv
from src.pdf_to_image import pdf_page_to_image
from src.arrow_detector import ArrowDetector

from src.association_engine import (
    get_text_near_destination,
    get_metragem_extendida,
    agrupar_palavras,
)

from src.excel_exporter import export_excel
from src.drawing_debug import create_debug_image

from src.info_parser import (
    parse_metragem,
    parse_material,
    parse_altura_poste,
    parse_logradouro,
    parse_ancoragem,
    detectar_logradouro,
)

from src.confidence import calcular_confianca
from src.auto_correct import corrigir_texto, DICIONARIO
from rapidfuzz import process as fuzz_process


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDITORIA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "run.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# TOKENS DESCONHECIDOS
# ─────────────────────────────────────────────
_token_logger = logging.getLogger("tokens")
_token_logger.setLevel(logging.INFO)

handler = logging.FileHandler(TOKENS_NAO_RECONHECIDOS_LOG, encoding="utf-8")
handler.setFormatter(logging.Formatter("%(message)s"))
_token_logger.addHandler(handler)

_tokens_ja_logados = set()


def _logar_token(token: str, contexto: str):
    chave = token.upper()
    if chave in _tokens_ja_logados:
        return
    _tokens_ja_logados.add(chave)

    result = fuzz_process.extractOne(token, DICIONARIO)
    sugestao = ""
    if result:
        txt, score, _ = result
        sugestao = f" | match: {txt} ({score:.0f}%)"

    _token_logger.info(f"DESCONHECIDO | {token} | {contexto}{sugestao}")


# ─────────────────────────────────────────────
# REGEX LOGRADOURO
# ─────────────────────────────────────────────
_LOGRADOURO_RE = re.compile(
    r"(RUA|AVENIDA|AV\.|ROD\.|RODOVIA|ESTRADA)\s+[A-Z0-9À-ÿ\.\- ]+",
    re.IGNORECASE
)


# ─────────────────────────────────────────────
# AGRUPAMENTO DE PDFs
# ─────────────────────────────────────────────
def group_pdfs_by_obra(input_dir: str):
    grupos = defaultdict(list)

    for f in os.listdir(input_dir):
        if f.lower().endswith(".pdf"):
            path = os.path.join(input_dir, f)
            obra = get_work_number(path)
            grupos[obra].append(path)

    for k in grupos:
        grupos[k].sort(key=get_sheet_number)

    return dict(grupos)


# ─────────────────────────────────────────────
# PROCESSAMENTO PDF
# ─────────────────────────────────────────────
def process_pdf(pdf_path: str):

    obra = get_work_number(pdf_path)
    folha = get_sheet_number(pdf_path)

    logger.info(f"Lendo {pdf_path} (obra={obra}, folha={folha})")

    words = read_pdf(pdf_path)
    pv_items = extract_pv(words)

    images = pdf_page_to_image(pdf_path, pages=[0])
    detector = ArrowDetector(images[0]) if images else None

    # ─────────────────────────────────────────────
    # AUDITORIA: imagem de debug com os pontos P/V detectados
    # (esta chamada estava ausente — por isso parou de gerar imagens)
    # ─────────────────────────────────────────────
    if images:
        debug_out = os.path.join(DEBUG_DIR, f"{obra}_folha{folha}_debug.png")
        try:
            create_debug_image(images[0], pv_items, debug_out)
            logger.info(f"Imagem de auditoria gerada: {debug_out}")
        except Exception as e:
            logger.error(f"Falha ao gerar imagem de auditoria: {e}")

    resultado = []

    for pv in pv_items:

        codigo = str(pv.get("codigo", "")).upper()
        page = pv.get("page", 1)

        # FIX POSTE / VÃO
        if "V" in codigo and "P" not in codigo:
            tipo = "VAO"
        elif "P" in codigo or "POSTE" in codigo:
            tipo = "POSTE"
        else:
            tipo = pv.get("tipo", "")
            if tipo not in ("POSTE", "VAO"):
                tipo = "POSTE" if "C" in codigo else "VAO"

        if detector is None:
            continue

        line = detector.find_nearest_line(
            pv["x"] * PDF_RENDER_SCALE,
            pv["y"] * PDF_RENDER_SCALE
        )

        if not line:
            continue

        dest = detector.line_destination(
            line,
            pv["x"] * PDF_RENDER_SCALE,
            pv["y"] * PDF_RENDER_SCALE
        )

        if not dest:
            continue

        dest_x, dest_y = dest

        blocos = agrupar_palavras(words, page=page)

        textos = get_text_near_destination(
            blocos,
            dest_x / PDF_RENDER_SCALE,
            dest_y / PDF_RENDER_SCALE,
            radius=ASSOCIATION_RADIUS,
            tipo=tipo,
            origin_x=pv["x"] * PDF_RENDER_SCALE,
            origin_y=pv["y"] * PDF_RENDER_SCALE,
        )

        # ─────────────────────────────────────────────
        # CORREÇÃO
        # ─────────────────────────────────────────────
        corrigidos = []
        houve_correcao = False

        for t in textos:
            r = corrigir_texto(t)
            corrigidos.append(r["corrigido"])
            if r["houve_correcao"]:
                houve_correcao = True

        textos = corrigidos

        # ─────────────────────────────────────────────
        # EXTRAÇÃO DOS CAMPOS DEDICADOS
        # Feita sobre a lista COMPLETA (antes da limpeza), senão os textos
        # de logradouro/ancoragem/lado forte seriam removidos antes de
        # serem lidos e as colunas ficariam sempre vazias.
        # ─────────────────────────────────────────────
        logradouro = parse_logradouro(textos)
        ancoragem  = parse_ancoragem(textos) if tipo == "POSTE" else ""

        # ─────────────────────────────────────────────
        # LIMPEZA (REMOVE O QUE JÁ FOI PARA COLUNA PRÓPRIA)
        # Evita que logradouro/ancoragem se repitam em "Informações".
        # ─────────────────────────────────────────────
        textos_limpos = []

        for t in textos:
            u = t.upper()

            if "ANCOR" in u:
                continue

            # remove logradouro de "Informações" — usa o mesmo detector
            # tolerante (pega também casos corrompidos tipo "ru2a")
            if detectar_logradouro(t):
                continue

            textos_limpos.append(t)

        # ─────────────────────────────────────────────
        # EXTRAÇÃO
        # ─────────────────────────────────────────────
        if tipo == "VAO":
            metragem = parse_metragem(textos_limpos)

            if not metragem and pv.get("metragem_colada"):
                metragem = pv["metragem_colada"]

            if not metragem:
                metragem = get_metragem_extendida(
                    words,
                    dest_x / PDF_RENDER_SCALE,
                    dest_y / PDF_RENDER_SCALE,
                    page=page,
                )

            material = ""
            altura_poste = ""

        else:
            metragem = ""
            material = parse_material(textos_limpos)
            altura_poste = parse_altura_poste(textos_limpos)

        confianca = calcular_confianca(
            metragem,
            material,
            altura_poste,
            textos_limpos,
        )

        if houve_correcao:
            confianca += 5

        confianca = min(confianca, 100)

        status = (
            "APROVADO" if confianca >= 80 else
            "REVISAR" if confianca >= 60 else
            "CRITICO"
        )

        resultado.append({
            "obra": obra,
            "folha": folha,
            "tipo": tipo,
            "codigo": codigo,
            "logradouro": logradouro,
            "ancoragem": ancoragem,
            "metragem": metragem,
            "material": material,
            "altura_poste": altura_poste,
            "informacoes": " | ".join(textos_limpos),
            "confianca": confianca,
            "status": status,
            "corrigido": "SIM" if houve_correcao else "NAO",
        })

    return resultado


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def _processar_obra(obra: str, pdfs: list[str]) -> str:
    """Processa todos os PDFs de uma obra e gera o Excel. Retorna o caminho."""
    todos = []
    for pdf in pdfs:
        try:
            todos.extend(process_pdf(pdf))
        except Exception as e:
            logger.error(f"Erro {pdf}: {e}")

    out = os.path.join(OUTPUT_DIR, f"{obra}.xlsx")
    export_excel(todos, out)
    print(f"EXCEL_GERADO:{out}")
    return out


def main(pdf_alvo: str | None = None):
    """
    Sem argumento: processa TODAS as obras de input_pdf (modo lote).
    Com um caminho de PDF: processa SOMENTE a obra daquele arquivo
    (junta as folhas da mesma obra presentes em input_pdf), sem reprocessar
    o resto da pasta.
    """
    grupos = group_pdfs_by_obra(INPUT_DIR)

    if pdf_alvo:
        obra_alvo = get_work_number(pdf_alvo)
        pdfs = grupos.get(obra_alvo, [pdf_alvo])
        logger.info(f"Processando apenas a obra {obra_alvo} ({len(pdfs)} folha(s)).")
        _processar_obra(obra_alvo, pdfs)
        return

    for obra, pdfs in grupos.items():
        _processar_obra(obra, pdfs)


if __name__ == "__main__":
    # aceita: python main.py  (lote)  |  python main.py "caminho/arquivo.pdf"
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    main(alvo)