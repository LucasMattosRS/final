from src.info_parser import parse_material


def test_material_inexistente():

    textos = ["ABC123"]

    resultado = parse_material(textos)

    assert resultado == ""