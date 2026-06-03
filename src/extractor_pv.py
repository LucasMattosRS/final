import re

_POSTE_RE = re.compile(r'^(POSTE-)?P\d+(-\d+)?$', re.IGNORECASE)
_VAO_RE = re.compile(r'^(VAO-)?V\d+-\d+$', re.IGNORECASE)


def extract_pv(words: list[dict]) -> list[dict]:
    itens = []
    for item in words:
        texto = item["text"].strip()
        if _POSTE_RE.match(texto):
            itens.append({
                "tipo": "POSTE",
                "codigo": texto,
                "page": item["page"],
                "x": item["x"],
                "y": item["y"],
            })
        elif _VAO_RE.match(texto):
            itens.append({
                "tipo": "VAO",
                "codigo": texto,
                "page": item["page"],
                "x": item["x"],
                "y": item["y"],
            })
    return itens
