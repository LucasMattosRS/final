from src.confidence import calcular_confianca


def test_status_aprovado():

    score = calcular_confianca(
        "35m",
        "CONCRETO",
        "11m",
        ["35m", "CONCRETO", "11m"]
    )

    assert score >= 80


def test_status_revisar():

    score = calcular_confianca(
        "",
        "CONCRETO",
        "11m",
        ["CONCRETO"]
    )

    assert 60 <= score < 80


def test_status_critico():

    score = calcular_confianca(
        "",
        "",
        "",
        []
    )

    assert score < 60