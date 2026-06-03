from main import process_pdf


def test_pdf_real():
    resultado = process_pdf(
        "tests/pdfs/planta_teste.pdf"
    )

    assert len(resultado) > 0