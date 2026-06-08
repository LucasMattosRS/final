import re


# -----------------------------------------------------------------------------
# Expressoes regulares
# -----------------------------------------------------------------------------

# Aceita:
# P5
# P5-1
# POSTE-P5
# POSTE-P5-1

_POSTE_RE = re.compile(
    r'\b(?:POSTE-)?P(\d+(?:-\d+)?)\b',
    re.IGNORECASE
)

# Aceita:
# V1-2
# V12-15
# V4-59.26m

_VAO_RE = re.compile(
    r'\bV(\d+)-(\d+)',
    re.IGNORECASE
)

# Captura:
# 9.26m
# 14,72m

_METRAGEM_COLADA_RE = re.compile(
    r'(\d+[.,]\d+)\s*m',
    re.IGNORECASE
)


# -----------------------------------------------------------------------------
# Extracao
# -----------------------------------------------------------------------------

def extract_pv(words: list[dict]) -> list[dict]:

    itens = []
    vistos = set()

    for item in words:

        texto = str(
            item["text"]
        ).strip()

        if not texto:
            continue

        # limpeza simples do OCR
        texto = (
            texto
            .replace("|", " ")
            .replace(";", " ")
            .replace(",", ",")
        )

        t = texto.upper()

        # ---------------------------------------------------------------------
        # POSTE
        # ---------------------------------------------------------------------

        m = _POSTE_RE.search(t)

        if m:

            codigo = f"P{m.group(1)}"

            chave = (
                codigo,
                item["page"]
            )

            if chave not in vistos:

                vistos.add(chave)

                itens.append(
                    {
                        "tipo": "POSTE",
                        "codigo": codigo,
                        "page": item["page"],
                        "x": item["x"],
                        "y": item["y"],
                        "info": "",
                    }
                )

            continue

        # ---------------------------------------------------------------------
        # VAO
        # ---------------------------------------------------------------------

        m = _VAO_RE.search(t)

        if m:

            codigo = (
                f"V{m.group(1)}-{m.group(2)}"
            )

            chave = (
                codigo,
                item["page"]
            )

            metragem_colada = ""

            mc = _METRAGEM_COLADA_RE.search(t)

            if mc:
                metragem_colada = (
                    mc.group(0)
                    .replace(",", ".")
                    .replace(" ", "")
                )

            if chave not in vistos:

                vistos.add(chave)

                itens.append(
                    {
                        "tipo": "VAO",
                        "codigo": codigo,
                        "page": item["page"],
                        "x": item["x"],
                        "y": item["y"],
                        "info": "",
                        "metragem_colada": metragem_colada,
                    }
                )

    return itens