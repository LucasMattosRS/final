from src.confidence import calcular_confianca


class TestConfidence:

    def test_confianca_alta(self):

        score = calcular_confianca(
            "35m",
            "CONCRETO",
            "11m",
            ["35m", "CONCRETO", "11m"]
        )

        assert score >= 80


    def test_confianca_media(self):

        score = calcular_confianca(
            "",
            "CONCRETO",
            "11m",
            ["CONCRETO"]
        )

        assert score >= 60


    def test_confianca_baixa(self):

        score = calcular_confianca(
            "",
            "",
            "",
            []
        )

        assert score < 60