"""
auto_correct.py
Correcao de tokens OCR usando dicionario extraido dos PDFs reais.
O dicionario pode ser carregado de:
  1. dicionario.json  (pasta raiz do projeto - editavel sem mexer no codigo)
  2. DICIONARIO_BASE  (embutido aqui como fallback)
"""

import re
import json
import os
from rapidfuzz import process

# ── Dicionario base embutido (fallback) ───────────────────────────────────────
DICIONARIO_BASE = [
    # Postes concreto + lista de equipamentos (tokens reais dos PDFs)
    "C09x300,SMPI,IP",
    "C09x300,SMPI,L1(2),IP",
    "C09x300,SMTG,IP",
    "C09x300,SMTG,L1(1),IP",
    "C09x600,L1(2),IP",
    "C09x600,SMFL,L1(1)",
    "C09x600,SMPI,L1(2),IP",
    "C10x300,B1M,SMTG",
    "C10x300,B2F,EPBFSA,SMTG",
    "C10x300,B4M,PRE4,SMFL,S45(1)",
    "C10x300,CE2,SMTG,IP",
    "C10x300,S145",
    "C10x600,B1M,ET1A,SMFL,S45(1)",
    "C10x600,B1M,M3F",
    "C10x600,ET4A,S144-2",
    "C12x1000,B4F,S44(1)",
    "C12x1000,CE2",
    "C12x1000,CE2-3LF,S44(1),L1(2),IP",
    "C12x1000,CE4,CE3,IP",
    "C12x1000,CE4,CE3,SMAN,IP",
    "C12x1000,CEAFC4,CE3,IP",
    "C12x300,B4F,CE2,S45(1),SMFL",
    "C12x300,CE-SH,ET4A,IP",
    "C12x300,CE1,IP",
    "C12x300,CE1A,S44(2),SMPI",
    "C12x300,CE2,L1(2),IP",
    "C12x300,CEAFC1,IP",
    "C12x300,CEAFS",
    "C12x300,CEAFS,1AF(1),IP",
    "C12x300,CEAFS,SMTG,L1(2),IP",
    "C12x600,B1F,CF-H",
    "C12x600,B1F,ET4A",
    "C12x600,B1M",
    "C12x600,B1M,CE2",
    "C12x600,B2F,M3F",
    "C12x600,B2M",
    "C12x600,B4A,BF-A",
    "C12x600,B4M",
    "C12x600,CE-SH,ET4A,IP",
    "C12x600,CE-SH,ET4A,S150-0,L1(2),IP",
    "C12x600,CE-SH,ET4A,SMTR,L1(2),IP",
    "C12x600,CE2,IP",
    "C12x600,CE2,SMTG,L1(2),IP",
    "C12x600,CE3,S144-1,IP",
    "C12x600,CE4,BF-A,IP",
    "C12x600,CE4,BF-A,SMTG,L1(2),IP",
    "C12x600,CE4,IP",
    "C14x1000,CE2",
    "C14x1000,CE4",
    # Postes madeira
    "M10x300,S43(1),S44(2),L1(1),IP",
    "M10x300,S43(3),L1(1),IP",
    "M10x600,S44(4),L1(2),IP",
    "M10x600,S45(3),L1(1)",
    "M10x600,SMPI,L1(2),IP",
    # Equipamentos isolados
    "SMFL", "SMPI", "SMDT", "SMAN", "SMTG", "SMTR",
    "SMFL,L1(1)", "SMFL,L1(2)", "SMFL,S45(3)",
    "SMDT,L1(1)", "SMTG,L1(1)", "SMTG,L1(2)", "SMTG,1AF(1)",
    "SMTR,L1(2)",
    # Classes de engenharia
    "CE1", "CE2", "CE3", "CE4", "CE-SH",
    "CEAFC1", "CEAFC4", "CEAFS", "CE2-3LF",
    # Classificacao de postes
    "S43(1)", "S43(3)", "S44(1)", "S44(2)", "S44(3)", "S44(4)",
    "S45(1)", "S45(3)", "S47(2)", "S143", "S144-1", "S144-2",
    "S145", "S150-0",
    "S44(2),SMPI", "S47(2),SMDT",
    # Ferragens
    "B1F", "B1M", "B2F", "B2M", "B4A", "B4F", "B4M",
    "BF-A", "CF-H", "M1F", "M1M", "M3F",
    # Protecoes
    "PRE1", "PRE3", "PRE4",
    "ET4A", "ET1A",
    # Iluminacao / ligacao
    "IP", "1AF(1)", "L1(1)", "L1(2)", "L2",
    # Cabos BT
    "1x3x120(70)AX", "1x3x240(120)AX", "1x3x70(70)AX",
    "1x3x70(70)AXNI(5AZN)",
    "2x1/0AN(4AN)", "2x1/0AN(4ANA)", "4x1/0AN",
    # Cabos MT
    "3x185AX(5AZN)", "3x70AX(5AZN)", "3x300AX-Q(6AZN)",
    "3x336AN", "3x336AN(3/0AN)",
    # Condutores multiplex
    "QX10", "QX16", "TX10", "TX16",
    # Transformadores
    "25KVA", "37,5KVA", "45KVA", "75KVA", "112,5KVA",
    # Tensao / rede
    "15KV_1F1(A)", "15KV_1L(C)", "15KV_1T(ABC)", "15KV_PDRT(ABC)",
    "BT", "MT", "BT0", "CORDOALHA",
    "RAMAL", "RAMAIS", "BIF", "TRIF",
    "BCU", "GD", "NF",
    "TRAFO", "BLINDAR", "REAPROVEITAR",
]

# Correcoes fixas de erros OCR conhecidos
_CORRECOES_FIXAS = {
    "C0GX600":   "C09X600",
    "C0GX1000":  "C09X1000",
    "SMFI":      "SMFL",
    "SMFIL":     "SMFL",
    "DTI1":      "DT11",
    "DTl1":      "DT11",
    "S442":      "S44(2)",
    "S462":      "S46(2)",
    "S472":      "S47(2)",
    "Ll(2)":     "L1(2)",
    "LI(2)":     "L1(2)",
    "LAD8O":     "LADO",
    "OC0R8":     "OCR",
    "RDOALHA":   "CORDOALHA",
    "37,E5KTVA": "37,5KVA",
    "550K8VA":   "50KVA",
    "CEL4,":     "CE4,",
    "1RU6A":     "1RAMAL",
    "P10BF":     "P10",
}

_FUZZY_THRESHOLD = 82


def _carregar_dicionario() -> list:
    """
    Carrega dicionario.json da raiz do projeto se existir.
    Formato aceito: lista JSON  ["C12x600", ...]
                 ou objeto JSON {"dicionario": ["C12x600", ...]}
    Se nao encontrar, retorna DICIONARIO_BASE.
    """
    json_path = os.path.join(os.path.dirname(__file__), "..", "dicionario.json")
    json_path = os.path.normpath(json_path)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
            if isinstance(dados, dict):
                return dados.get("dicionario", DICIONARIO_BASE)
        except Exception as e:
            print(f"[auto_correct] Aviso: nao foi possivel ler dicionario.json ({e}). Usando base embutida.")
    return DICIONARIO_BASE


DICIONARIO = _carregar_dicionario()


def corrigir_token(token: str) -> str:
    resultado = process.extractOne(token, DICIONARIO)
    if resultado:
        texto, score, _ = resultado
        if score >= _FUZZY_THRESHOLD:
            return texto
    return token


def corrigir_texto(texto: str) -> dict:
    original = texto
    upper = texto.upper()

    # 1. Correcoes fixas
    for erro, correto in _CORRECOES_FIXAS.items():
        upper = upper.replace(erro.upper(), correto)

    # 2. Fuzzy token a token (separa por virgula/espaco)
    partes = re.split(r'([,\s]+)', upper)
    saida = []
    houve = False
    for parte in partes:
        p = parte.strip()
        if p:
            corrigido = corrigir_token(p)
            if corrigido != p:
                houve = True
            saida.append(corrigido)
        else:
            saida.append(parte)

    resultado_final = "".join(saida)
    houve = houve or (resultado_final != original.upper())

    return {
        "original": original,
        "corrigido": resultado_final,
        "houve_correcao": houve,
    }
