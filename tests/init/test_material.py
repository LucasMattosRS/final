from src.info_parser import parse_material


def test_material_dt():
    textos = ["POSTE DT 11m"]

    resultado = parse_material(textos)

    assert resultado in ["DT", "CONCRETO", "MADEIRA", ""]