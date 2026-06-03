import re

# ── Problema 1 corrigido ──────────────────────────────────────────────────────
# Regex antigo: ^P\d+(-\d+)?$  -- nao capturava "POSTE-P5"
# Regex antigo: ^V\d+-\d+$     -- nao capturava metragem colada (ex: "V4-59.26m")
#
# Solucoes:
#   - POSTE: aceita prefixo "POSTE-" opcional, strip() antes de testar,
#     e usa search() em vez de match() para pegar P5 dentro de "P5|CONEX.|P4-30"
#   - VAO: aceita o codigo mesmo com texto colado apos ele (ex: "V4-59.26m")
#     e extrai o codigo limpo separado da metragem eventual

_POSTE_RE = re.compile(r'(?:POSTE-)?P(\d+(?:-\d+)?)', re.IGNORECASE)
_VAO_RE   = re.compile(r'V(\d+)-(\d+)',               re.IGNORECASE)

# Metragem colada ao codigo do vao, ex: "V4-59.26m" -> 9.26m
_METRAGEM_COLADA_RE = re.compile(r'(\d+[.,]\d+)\s*m', re.IGNORECASE)


def extract_pv(words: list[dict]) -> list[dict]:
    """
    Percorre a lista de palavras e retorna rotulos P/V.

    Melhorias:
    - Faz strip() e upper() antes de testar para eliminar espacos/encoding.
    - Usa search() no lugar de match() para capturar codigos que vem
      grudados com texto vizinho (ex: "P5|CONEX.", "POSTE-P5").
    - Extrai metragem colada ao codigo do vao quando existir.
    """
    itens = []
    vistos = set()   # evita duplicatas se o mesmo codigo aparecer 2x

    for item in words:
        texto = item["text"].strip()
        if not texto:
            continue

        t = texto.upper()

        # ── Testa POSTE ───────────────────────────────────────────────────────
        m = _POSTE_RE.search(t)
        if m:
            codigo = f"P{m.group(1)}"
            chave  = (codigo, item["page"])
            if chave not in vistos:
                vistos.add(chave)
                itens.append({
                    "tipo":      "POSTE",
                    "codigo":    codigo,
                    "page":      item["page"],
                    "x":         item["x"],
                    "y":         item["y"],
                    "info":      "",
                })
            continue

        # ── Testa VAO ─────────────────────────────────────────────────────────
        m = _VAO_RE.search(t)
        if m:
            codigo   = f"V{m.group(1)}-{m.group(2)}"
            chave    = (codigo, item["page"])

            # Captura metragem colada se houver (ex: "V4-59.26m")
            metragem_colada = ""
            mc = _METRAGEM_COLADA_RE.search(t)
            if mc:
                metragem_colada = mc.group(0).replace(",", ".")

            if chave not in vistos:
                vistos.add(chave)
                itens.append({
                    "tipo":             "VAO",
                    "codigo":           codigo,
                    "page":             item["page"],
                    "x":                item["x"],
                    "y":                item["y"],
                    "info":             "",
                    "metragem_colada":  metragem_colada,
                })

    return itens
