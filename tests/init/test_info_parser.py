"""
Testes unitários para src/info_parser.py
Execute com: python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.info_parser import parse_metragem, parse_material, parse_altura_poste


# ── parse_metragem ────────────────────────────────────────────────────────────

class TestParseMetragem:

    def test_token_simples_metros(self):
        assert parse_metragem(["9.26m"]) == "9.26m"

    def test_token_virgula(self):
        assert parse_metragem(["35,5m"]) == "35,5m"

    def test_token_maiusculo(self):
        assert parse_metragem(["30M"]) == "30m"

    def test_numero_separado_de_m(self):
        # "32.86" como token, "m" como próximo token
        assert parse_metragem(["V9-10", "1x3x70(70)AXNI", "32.86", "m"]) == "32.86m"

    def test_varios_tokens_pega_primeiro(self):
        result = parse_metragem(["46.07m", "46.07m"])
        assert result == "46.07m"

    def test_sem_metragem(self):
        assert parse_metragem(["POSTE", "C09x600", "SMFL"]) == ""

    def test_lista_vazia(self):
        assert parse_metragem([]) == ""

    def test_metragem_dentro_de_string(self):
        # Fallback: extrai de substring
        result = parse_metragem(["cabos 12,5m comprimento"])
        assert result == "12,5m"


# ── parse_material ────────────────────────────────────────────────────────────

class TestParseMaterial:

    def test_codigo_concreto(self):
        assert parse_material(["C09x600,SMFL,L1(1)"]) == "CONCRETO"

    def test_codigo_madeira(self):
        assert parse_material(["M10x300,S43(3),L1(1),IP"]) == "MADEIRA"

    def test_token_isolado_c(self):
        assert parse_material(["C"]) == "CONCRETO"

    def test_token_isolado_m(self):
        assert parse_material(["M"]) == "MADEIRA"

    def test_codigo_tem_prioridade_sobre_token(self):
        # Token C aparece depois do código M → deve retornar MADEIRA
        assert parse_material(["M10x600,SMPI", "C"]) == "MADEIRA"

    def test_sem_material(self):
        assert parse_material(["INSTALAR", "POSTE", "AO", "LADO"]) == ""

    def test_lista_vazia(self):
        assert parse_material([]) == ""

    def test_c12(self):
        assert parse_material(["C12x600,B4A,BF-A"]) == "CONCRETO"


# ── parse_altura_poste ────────────────────────────────────────────────────────

class TestParseAlturaPoste:

    def test_altura_09(self):
        assert parse_altura_poste(["C09x600,SMFL"]) == "9m"

    def test_altura_10(self):
        assert parse_altura_poste(["M10x300,S43(3)"]) == "10m"

    def test_altura_12(self):
        assert parse_altura_poste(["C12x600,CE3"]) == "12m"

    def test_sem_codigo(self):
        assert parse_altura_poste(["INSTALAR", "C"]) == ""
