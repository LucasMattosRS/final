import math
import re


# -----------------------------------------------------------------------------
# UTILITÁRIOS
# -----------------------------------------------------------------------------

def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def esta_na_direcao(
    origem_x: float,
    origem_y: float,
    destino_x: float,
    destino_y: float,
    texto_x: float,
    texto_y: float,
    angulo_max: float = 35,
) -> bool:

    vx = destino_x - origem_x
    vy = destino_y - origem_y

    tx = texto_x - destino_x
    ty = texto_y - destino_y

    nv = math.hypot(vx, vy)
    nt = math.hypot(tx, ty)

    if nv == 0 or nt == 0:
        return True

    produto = (vx * tx) + (vy * ty)
    cosangulo = produto / (nv * nt)

    cosangulo = max(-1.0, min(1.0, cosangulo))

    angulo = math.degrees(math.acos(cosangulo))

    return angulo <= angulo_max


# -----------------------------------------------------------------------------
# REGEX
# -----------------------------------------------------------------------------

_METRAGEM_RE = re.compile(r'\d+[.,]\d+\s*m', re.IGNORECASE)


# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

_MAX_DISTANCE = 250


# -----------------------------------------------------------------------------
# SCORE BASE
# -----------------------------------------------------------------------------

def _dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _normalize_distance(d):
    return max(0.0, 1.0 - (d / _MAX_DISTANCE))


def _semantic_score(text, tipo):
    t = text.upper()

    if tipo == "POSTE":
        score = 0.0

        if "C" in t and "X" in t:
            score += 0.4

        if "S" in t and "(" in t:
            score += 0.3

        if "CONCRETO" in t or "MADEIRA" in t:
            score += 0.3

        if "M" in t and len(t) < 5:
            score -= 0.8

        # 🔥 anti-vão dentro de poste
        if "VAO" in t or "VÃO" in t:
            score -= 1.0

        return score

    if tipo == "VAO":
        score = 0.0

        if "M" in t:
            score += 0.6

        if any(c.isdigit() for c in t):
            score += 0.2

        if "C" in t and "X" in t:
            score -= 1.0

        # 🔥 anti-poste dentro de vão
        if "POSTE" in t:
            score -= 1.0

        return score

    return 0.0


def _direction_score(px, py, dx, dy, tx, ty):
    vx, vy = dx - px, dy - py
    tx, ty = tx - px, ty - py

    dot = vx * tx + vy * ty
    mag_v = math.sqrt(vx * vx + vy * vy)
    mag_t = math.sqrt(tx * tx + ty * ty)

    if mag_v == 0 or mag_t == 0:
        return 0

    return max(0.0, dot / (mag_v * mag_t))


# -----------------------------------------------------------------------------
# DETECÇÃO DE TIPO (FIXO)
# -----------------------------------------------------------------------------

def _detect_tipo(texto: str) -> str:
    t = texto.upper()

    if "POSTE" in t or ("C" in t and "X" in t):
        return "POSTE"

    if "VAO" in t or "VÃO" in t:
        return "VAO"

    if re.search(r"\d+[.,]?\d*\s*M", t):
        return "VAO"

    return "GEN"


# -----------------------------------------------------------------------------
# ENGINE PRINCIPAL
# -----------------------------------------------------------------------------

def get_text_near_destination(
    blocos,
    dest_x,
    dest_y,
    radius=150,
    page=None,
    tipo=None,
    origin_x=None,
    origin_y=None,
    debug=False,
):

    candidatos = []

    for b in blocos:

        bx = b.get("x", 0)
        by = b.get("y", 0)
        text = b.get("text", "")

        d = _dist(bx, by, dest_x, dest_y)

        if d > radius * 2:
            continue

        # 🔥 DETECTA TIPO DO TEXTO
        tipo_detectado = _detect_tipo(text)

        # 🔥 BLOQUEIO CRUZADO (ESSENCIAL)
        if tipo == "POSTE" and tipo_detectado == "VAO":
            continue

        if tipo == "VAO" and tipo_detectado == "POSTE":
            continue

        score = 0.0
        score += _normalize_distance(d) * 0.5
        score += _semantic_score(text, tipo) * 0.4

        if origin_x is not None and origin_y is not None:
            score += _direction_score(origin_x, origin_y, dest_x, dest_y, bx, by) * 0.1

        candidatos.append((score, text, d))

    candidatos.sort(key=lambda x: x[0], reverse=True)

    if debug:
        print("\n[DEBUG SCORE]")
        for s, t, d in candidatos[:10]:
            print(f"{s:.3f} | {d:.1f} | {t}")

    if not candidatos:
        return []

    return [c[1] for c in candidatos[:8]]


# -----------------------------------------------------------------------------
# METRAGEM EXTENDIDA
# -----------------------------------------------------------------------------

def get_metragem_extendida(words, dest_x, dest_y, page=1, raio_max=150):

    candidatos = []

    for w in words:

        if w["page"] != page:
            continue

        t = str(w["text"])

        if not _METRAGEM_RE.search(t):
            continue

        d = _distance(dest_x, dest_y, w["x"], w["y"])

        if d > raio_max:
            continue

        candidatos.append((d, t))

    if not candidatos:
        return ""

    candidatos.sort(key=lambda x: x[0])
    return candidatos[0][1]


# -----------------------------------------------------------------------------
# AGRUPAMENTO
# -----------------------------------------------------------------------------

def agrupar_palavras(words, page=1, dist_x=45, dist_y=10):

    palavras = [w.copy() for w in words if w["page"] == page]
    palavras.sort(key=lambda p: (p["y"], p["x"]))

    usados = set()
    grupos = []

    for i, base in enumerate(palavras):

        if i in usados:
            continue

        usados.add(i)

        grupo = [base]

        for j, outra in enumerate(palavras):

            if j in usados:
                continue

            dx = abs(base["x"] - outra["x"])
            dy = abs(base["y"] - outra["y"])

            if dx <= dist_x and dy <= dist_y:
                grupo.append(outra)
                usados.add(j)

        grupo.sort(key=lambda x: x["x"])

        texto = " ".join(str(x["text"]).strip() for x in grupo if str(x["text"]).strip())

        grupos.append({
            "page": page,
            "text": texto,
            "x": sum(x["x"] for x in grupo) / len(grupo),
            "y": sum(x["y"] for x in grupo) / len(grupo),
        })

    return grupos