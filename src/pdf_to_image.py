import os
import pypdfium2 as pdfium
from config import TEMP_DIR, PDF_RENDER_SCALE


def pdf_page_to_image(
    pdf_path: str,
    pages: list[int] | None = None,
    output_dir: str = TEMP_DIR,
    scale: int = PDF_RENDER_SCALE,
) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)

    if pages is None:
        pages = [0]

    pdf = pdfium.PdfDocument(pdf_path)
    result = []

    for page_num in pages:
        if page_num >= len(pdf):
            continue
        page = pdf[page_num]
        bitmap = page.render(scale=scale)
        pil_img = bitmap.to_pil()
        out_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
        pil_img.save(out_path)
        result.append(out_path)

    return result