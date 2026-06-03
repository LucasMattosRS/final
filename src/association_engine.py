import math


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_text_near_destination(
    words: list[dict],
    dest_x: float,
    dest_y: float,
    radius: float = 60,
    page: int = 1,
) -> list[str]:
    """
    Retorna os textos dentro de `radius` unidades do ponto (dest_x, dest_y)
    **na mesma página**, ordenados por distância crescente.
    Filtrar por página evita que textos de outras folhas contaminem o resultado.
    """
    resultado = []
    for word in words:
        if word["page"] != page:
            continue
        d = _distance(dest_x, dest_y, word["x"], word["y"])
        if d <= radius:
            resultado.append((d, word["text"]))

    resultado.sort(key=lambda t: t[0])
    return [text for _, text in resultado]
