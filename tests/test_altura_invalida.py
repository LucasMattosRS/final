from src.info_parser import parse_altura_poste


def test_altura_inexistente():

    textos = ["POSTE"]

    resultado = parse_altura_poste(textos)

    assert resultado == ""