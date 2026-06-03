import os

from src.excel_exporter import export_excel


def test_cria_excel():

    dados = [
        {
            "obra": "123",
            "folha": 1,
            "tipo": "POSTE",
            "codigo": "P1",
            "metragem": "",
            "material": "CONCRETO",
            "altura_poste": "11m",
            "informacoes": "teste",
            "confianca": 95,
            "status": "APROVADO"
        }
    ]

    arquivo = "teste.xlsx"

    export_excel(dados, arquivo)

    assert os.path.exists(arquivo)

    os.remove(arquivo)