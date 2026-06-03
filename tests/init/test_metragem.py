from src.info_parser import parse_metragem


def test_metragem_35():
    textos = ["VÃO", "35m"]

    resultado = parse_metragem(textos)

    assert resultado == "35m"


def test_metragem_120():
    textos = ["120m"]

    resultado = parse_metragem(textos)

    assert resultado == "120m"