"""
Automacao de leitura de plantas eletricas/estruturais em PDF.

Fluxo:
  1. Agrupa PDFs por codigo de obra (prefixo numerico do nome do arquivo).
  2. Para cada grupo, processa todos os PDFs e gera UM unico Excel por obra.
  3. Dentro de cada PDF, detecta rotulos P (poste) e V (vao), segue a seta
     ate o destino e extrai: metragem (V) ou material/altura (P).
"""

import os
import sys
import logging
from collections import defaultdict
from config import AUDITORIA_DIR, TOKENS_NAO_RECONHECIDOS_LOG
from config import INPUT_DIR, OUTPUT_DIR, DEBUG_DIR, LOG_DIR, PDF_RENDER_SCALE, ASSOCIATION_RADIUS
from src.work_number import get_work_number, get_sheet_number
from src.pdf_reader import read_pdf
from src.extractor_pv import extract_pv
from src.pdf_to_image import pdf_page_to_image
from src.arrow_detector import ArrowDetector
from src.association_engine import get_text_near_destination, get_metragem_extendida
from src.excel_exporter import export_excel
from src.drawing_debug import create_debug_image
from src.info_parser import parse_metragem, parse_material, parse_altura_poste
from src.confidence import calcular_confianca
from src.auto_correct import corrigir_texto, DICIONARIO

from rapidfuzz import process as fuzz_process

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDITORIA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "run.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Logger separado para tokens nao reconhecidos
_token_logger = logging.getLogger("tokens_desconhecidos")
_token_logger.setLevel(logging.INFO)
_token_logger.propagate = False
_tfh = logging.FileHandler(TOKENS_NAO_RECONHECIDOS_LOG, encoding="utf-8")
_tfh.setFormatter(logging.Formatter("%(message)s"))
_token_logger.addHandler(_tfh)

# Conjunto em memoria para nao repetir o mesmo token no log da sessao
_tokens_ja_logados: set[str] = set()


def _logar_token_desconhecido(token: str, contexto: str) -> None:
    """
    Loga tokens que nao bateram no dicionario com score >= 82.
    Evita duplicatas dentro da mesma execucao.
    """
    chave = token.upper()
    if chave in _tokens_ja_logados:
        return
    _tokens_ja_logados.add(chave)

    # Tenta mostrar o candidato mais proximo mesmo abaixo do limiar
    resultado = fuzz_process.extractOne(token, DICIONARIO)
    sugestao = ""
    if resultado:
        texto, score, _ = resultado
        sugestao = f" | melhor match: '{texto}' ({score:.0f}%)"

    _token_logger.info("DESCONHECIDO | %s | contexto: %s%s", token, contexto, sugestao)


# ── Agrupamento de PDFs por obra ──────────────────────────────────────────────

def group_pdfs_by_obra(input_dir: str) -> dict[str, list[str]]:
    grupos: dict[str, list[str]] = defaultdict(list)
    for file_name in os.listdir(input_dir):
        if not file_name.lower().endswith(".pdf"):
            continue
        full_path = os.path.join(input_dir, file_name)
        obra = get_work_number(full_path)
        grupos[obra].append(full_path)

    for obra in grupos:
        grupos[obra].sort(key=get_sheet_number)

    return dict(grupos)


# ── Processamento de um unico PDF ─────────────────────────────────────────────

def process_pdf(pdf_path: str) -> list[dict]:
    obra  = get_work_number(pdf_path)
    folha = get_sheet_number(pdf_path)

    logger.info("  Lendo PDF: %s (obra=%s, folha=%d)", os.path.basename(pdf_path), obra, folha)

    words    = read_pdf(pdf_path)
    pv_items = extract_pv(words)

    for item in pv_items:
        item["info"] = ""

    logger.info("  P/V encontrados: %d", len(pv_items))

    images = pdf_page_to_image(pdf_path, pages=[0])

    if images:
        auditoria_out = os.path.join(AUDITORIA_DIR, f"{obra}_folha{folha}_auditoria.png")
        create_debug_image(images[0], pv_items, auditoria_out)
        detector = ArrowDetector(images[0])
    else:
        logger.warning("  Nao foi possivel renderizar imagem de %s", pdf_path)
        detector = None

    resultado = []
    scale = PDF_RENDER_SCALE

    for pv in pv_items:

        tipo   = pv["tipo"]
        codigo = pv["codigo"]
        page   = pv["page"]
        pv["info"] = ""

        if detector is None:
            logger.warning("  [%s] Detector indisponivel", codigo)
            continue

        line = detector.find_nearest_line(
            pv["x"] * scale,
            pv["y"] * scale
        )
        if line is None:
            logger.warning("  [%s] Linha nao encontrada", codigo)
            continue

        destination = detector.line_destination(line, pv["x"] * scale, pv["y"] * scale)
        if destination is None:
            logger.warning("  [%s] Destino nao encontrado", codigo)
            continue

        dest_x, dest_y = destination

        textos = get_text_near_destination(
            words,
            dest_x / scale,
            dest_y / scale,
            radius=ASSOCIATION_RADIUS,
            page=page,
        )

        # ── Correcao e log de tokens desconhecidos ────────────────────────────
        novos_textos    = []
        houve_correcao  = False

        for t in textos:
            res = corrigir_texto(t)
            novos_textos.append(res["corrigido"])
            if res["corrigido"] == t.upper():
                # Token nao foi corrigido - verifica se e desconhecido
                # (ignora numeros, metragens, codigos de obra e tokens muito curtos)
                if len(t) >= 3 and not t.replace(".", "").replace(",", "").replace("m", "").isdigit():
                    _logar_token_desconhecido(t, codigo)
            if res["houve_correcao"]:
                houve_correcao = True

        textos = novos_textos

        # ── Extracao especifica por tipo ──────────────────────────────────────
        if tipo == "VAO":
            metragem = parse_metragem(textos)
            # Problema 5: metragem pode estar num token separado fora do raio primario
            # Tenta tambem a metragem colada ao codigo do vao (ex: "V4-59.26m")
            if not metragem and pv.get("metragem_colada"):
                metragem = pv["metragem_colada"]
            # Ultimo fallback: busca metragem em raio maior
            if not metragem:
                metragem = get_metragem_extendida(
                    words, dest_x / scale, dest_y / scale, page=page
                )
            material     = ""
            altura_poste = ""
        else:  # POSTE
            metragem     = ""
            material     = parse_material(textos)
            altura_poste = parse_altura_poste(textos)

        confianca = calcular_confianca(metragem, material, altura_poste, textos)

        if houve_correcao:
            confianca += 5
        confianca = min(confianca, 100)

        if confianca >= 80:
            status = "APROVADO"
        elif confianca >= 60:
            status = "REVISAR"
        else:
            status = "CRITICO"

        info_parts = []
        if material:
            info_parts.append(material)
        if metragem:
            info_parts.append(metragem)
        if altura_poste:
            info_parts.append(altura_poste)

        pv["info"] = " | ".join(info_parts)

        resultado.append({
            "obra":         obra,
            "folha":        folha,
            "tipo":         tipo,
            "codigo":       codigo,
            "metragem":     metragem,
            "material":     material,
            "altura_poste": altura_poste,
            "informacoes":  " | ".join(textos),
            "confianca":    confianca,
            "status":       status,
            "corrigido":    "SIM" if houve_correcao else "NAO",
        })

    return resultado


# ── Chamada automatica do atualizador de dicionario ──────────────────────────

def atualizar_dicionario_pos_execucao() -> None:
    """
    Roda atualizar_dicionario.py --auto automaticamente apos processar todos os PDFs.
    Tokens novos (score < 70) sao adicionados sem perguntar.
    Tokens ambiguos (score >= 70) sao listados para revisao manual.
    """
    import subprocess
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atualizar_dicionario.py")
    if not os.path.exists(script):
        return
    logger.info("Atualizando dicionario.json com tokens novos...")
    subprocess.run([sys.executable, script, "--auto"], check=False)

# ── Orquestrador principal ────────────────────────────────────────────────────

def main() -> None:
    grupos = group_pdfs_by_obra(INPUT_DIR)

    if not grupos:
        logger.warning("Nenhum PDF encontrado em: %s", INPUT_DIR)
        return

    logger.info("Obras encontradas: %d | PDFs totais: %d",
                len(grupos), sum(len(v) for v in grupos.values()))

    for obra, pdf_paths in sorted(grupos.items()):
        logger.info("=== Processando obra %s (%d PDF(s)) ===", obra, len(pdf_paths))

        todos_resultados: list[dict] = []
        for pdf_path in pdf_paths:
            try:
                parcial = process_pdf(pdf_path)
                todos_resultados.extend(parcial)
            except Exception as exc:
                logger.error("  Erro ao processar %s: %s", pdf_path, exc, exc_info=True)

        excel_name  = f"{obra}.xlsx"
        output_file = os.path.join(OUTPUT_DIR, excel_name)
        export_excel(todos_resultados, output_file)
        logger.info("  Excel gerado: %s (%d registros)", excel_name, len(todos_resultados))
        print(f"EXCEL_GERADO:{output_file}")

    # Resumo final de tokens desconhecidos
    if _tokens_ja_logados:
        logger.info(
            "Tokens nao reconhecidos nesta execucao: %d — veja %s",
            len(_tokens_ja_logados),
            TOKENS_NAO_RECONHECIDOS_LOG,
        )
        # Atualiza dicionario.json automaticamente com tokens novos
        atualizar_dicionario_pos_execucao()
    else:
        logger.info("Nenhum token desconhecido encontrado.")


if __name__ == "__main__":
    main()

