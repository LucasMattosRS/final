from main import process_pdf


def test_pdf_sem_pontos():

    resultado = process_pdf(
        "tests/pdfs/pdf_vazio.pdf"
    )

    assert len(resultado) == 0