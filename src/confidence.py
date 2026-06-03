import re

def calcular_confianca(
    metragem,
    material,
    altura_poste,
    textos
):

    score = 0

    if metragem:
        score += 30

    if material:
        score += 30

    if altura_poste:
        score += 20

    if textos:
        score += 10

    texto_completo = " ".join(textos)

    if re.search(
        r"\d+\s*m",
        texto_completo,
        re.IGNORECASE
    ):
        score += 10

    return min(score, 100)