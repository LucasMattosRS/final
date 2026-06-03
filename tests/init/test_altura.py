from src.info_parser import parse_altura_poste


def test_altura_09():
    assert parse_altura_poste(
        ["C09x600,SMFL"]
    ) == "9m"


def test_altura_12():
    assert parse_altura_poste(
        ["C12x600,CE3"]
    ) == "12m"


def test_sem_altura():
    assert parse_altura_poste(
        ["POSTE"]
    ) == ""