import math


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ── Problema 4 corrigido ──────────────────────────────────────────────────────
# Raio unico de 90 capturava texto de postes vizinhos.
# Solucao: busca em duas passagens (raio pequeno primeiro, raio maior so
# se a primeira nao retornar resultados uteis) + filtra tokens que sao
# claramente rotulos P/V de outros postes vizinhos.

import re
_OUTRO_PV_RE = re.compile(r'^(POSTE-)?[PV]\d+(-\d+)?$', re.IGNORECASE)

RAIO_PRIMARIO   = 55   # busca primeiro num raio menor
RAIO_SECUNDARIO = 90   # expande so se nao encontrar nada util


def get_text_near_destination(
    words: list[dict],
    dest_x: float,
    dest_y: float,
    radius: float = RAIO_PRIMARIO,
    page: int = 1,
) -> list[str]:
    """
    Retorna textos proximos ao destino da seta, na mesma pagina.

    Melhorias:
    - Busca em raio primario (55); se retornar menos de 2 tokens uteis,
      expande para raio secundario (90).
    - Remove tokens que sao rotulos P/V de outros postes vizinhos
      para evitar contaminacao cruzada.
    - Ordena por distancia crescente (mais proximo primeiro).
    """

    def _coletar(r: float) -> list[tuple[float, str]]:
        resultado = []
        for word in words:
            if word["page"] != page:
                continue
            d = _distance(dest_x, dest_y, word["x"], word["y"])
            if d <= r:
                texto = word["text"].strip()
                # Ignora rotulos de outros postes/vaos vizinhos
                if _OUTRO_PV_RE.match(texto):
                    continue
                resultado.append((d, texto))
        resultado.sort(key=lambda t: t[0])
        return resultado

    # Passagem 1: raio pequeno
    encontrados = _coletar(RAIO_PRIMARIO)

    # Passagem 2: expande se encontrou menos de 2 tokens com conteudo
    tokens_uteis = [t for _, t in encontrados if len(t) >= 3]
    if len(tokens_uteis) < 2:
        encontrados = _coletar(RAIO_SECUNDARIO)

    return [texto for _, texto in encontrados]


# ── Problema 5 corrigido ──────────────────────────────────────────────────────
# Vaos como V4-5 tinham a metragem (ex: 9.26m) num token separado,
# fora do raio da ponta da seta. Funcao auxiliar para buscar a metragem
# num raio estendido quando a busca normal nao encontrou nenhuma metragem.

_METRAGEM_RE = re.compile(r'\d+[.,]\d+\s*m', re.IGNORECASE)


def get_metragem_extendida(
    words: list[dict],
    dest_x: float,
    dest_y: float,
    page: int = 1,
    raio_max: float = 150,
) -> str:
    """
    Busca especificamente uma metragem (ex: 9.26m, 14.72m) num raio maior.
    Usado como fallback quando get_text_near_destination nao retornou metragem.
    Retorna a metragem mais proxima encontrada ou string vazia.
    """
    candidatos = []
    for word in words:
        if word["page"] != page:
            continue
        texto = word["text"].strip()
        if _METRAGEM_RE.search(texto):
            d = _distance(dest_x, dest_y, word["x"], word["y"])
            if d <= raio_max:
                candidatos.append((d, texto))

    if not candidatos:
        return ""

    candidatos.sort(key=lambda t: t[0])
    return candidatos[0][1]
