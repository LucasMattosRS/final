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
    parse_lado_forte,
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
        # LIMPEZA (REMOVE LOGRADOURO + RUÍDOS)
        # ─────────────────────────────────────────────
        textos_limpos = []

        for t in textos:
            u = t.upper()

            if "ANCORAR" in u:
                continue
            if "LADO FORTE" in u:
                continue

            # remove logradouro da coluna informações
            if _LOGRADOURO_RE.search(t):
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

        logradouro = parse_logradouro(textos_limpos)

        ancoragem = parse_ancoragem(textos_limpos) if tipo == "POSTE" else ""
        lado_forte = parse_lado_forte(textos_limpos) if tipo == "POSTE" else ""

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
            "lado_forte": lado_forte,
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
def main():

    grupos = group_pdfs_by_obra(INPUT_DIR)

    for obra, pdfs in grupos.items():

        todos = []

        for pdf in pdfs:
            try:
                todos.extend(process_pdf(pdf))
            except Exception as e:
                logger.error(f"Erro {pdf}: {e}")

        out = os.path.join(OUTPUT_DIR, f"{obra}.xlsx")
        export_excel(todos, out)

        print(f"EXCEL_GERADO:{out}")


if __name__ == "__main__":
    main()