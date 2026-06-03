import pdfplumber


def read_pdf(pdf_path: str) -> list[dict]:
    """
    Lê todas as palavras do PDF e retorna lista de dicts com
    page, text, x, y (canto superior esquerdo da bounding box).
    """
    resultado = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for w in page.extract_words():
                resultado.append({
                    "page": page_num + 1,
                    "text": w["text"],
                    "x": w["x0"],
                    "y": w["top"],
                })
    return resultado
